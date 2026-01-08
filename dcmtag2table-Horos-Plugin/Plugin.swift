//
// Plugin.swift
// dcmtag2table
//
// Horos plugin that exports DICOM tags (one row per series) to CSV.
//
// Thales Matheus Mendonca Santos - January 2026
//

import Cocoa

// Captures process termination and output so the caller can decide how to report results.
private struct ProcessExecutionResult {
    let terminationStatus: Int32
    let stdout: Data
    let stderr: Data
    let error: Error?
}

// Encapsulates a resolved Python interpreter with optional arguments and environment.
private typealias ExecutableResolution = (
    executableURL: URL,
    leadingArguments: [String],
    environment: [String: String]?
)

private struct SeriesManifestEntry: Codable {
    let filePath: String
    let studyInstanceUID: String?
    let seriesInstanceUID: String?

    enum CodingKeys: String, CodingKey {
        case filePath = "file_path"
        case studyInstanceUID = "study_instance_uid"
        case seriesInstanceUID = "series_instance_uid"
    }
}

private struct SeriesManifest: Codable {
    let series: [SeriesManifestEntry]
}

@objc(Dcmtag2tablePlugin)
class Dcmtag2tablePlugin: PluginFilter {
    private enum MenuAction: String {
        case exportTags = "dcmtag2table"
    }

    override func filterImage(_ menuName: String!) -> Int {
        logToConsole("filterImage invoked for menu action: \(menuName ?? "nil")")
        guard let menuName = menuName,
              let action = MenuAction(rawValue: menuName) else {
            NSLog("Dcmtag2tablePlugin received unsupported menu action: %@", menuName ?? "nil")
            presentAlert(title: "dcmtag2table", message: "Unsupported action selected.")
            return 0
        }

        switch action {
        case .exportTags:
            startRunFlow()
        }

        return 0
    }

    override func initPlugin() {
        NSLog("Dcmtag2tablePlugin loaded and ready.")
    }

    override func isCertifiedForMedicalImaging() -> Bool {
        return true
    }

    private func startRunFlow() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.runExportFlow()
        }
    }

    private func runExportFlow() {
        do {
            // Ensure managed Python environment is ready
            guard let pythonResolution = ensureManagedEnvironment() else {
                presentAlert(title: "dcmtag2table", message: "Unable to prepare Python environment. Please check that Python 3 is installed on your system.")
                return
            }

            let outputDir = try ensureOutputDirectory()
            let manifestURL = try buildManifestFile(in: outputDir)

            guard let scriptURL = resolveScriptURL() else {
                presentAlert(title: "dcmtag2table", message: "Unable to locate python_script/main.py in the plugin bundle.")
                return
            }

            let tagsFileURL = outputDir.appendingPathComponent("tags.txt")
            let tagsFileArgument = FileManager.default.fileExists(atPath: tagsFileURL.path) ? tagsFileURL : nil

            // Build arguments for the Python script (without the "python3" prefix)
            var scriptArguments = [scriptURL.path, "--manifest", manifestURL.path, "--output-dir", outputDir.path]
            if let tagsFileURL = tagsFileArgument {
                scriptArguments.append(contentsOf: ["--tags-file", tagsFileURL.path])
            }

            let scriptDirectory = scriptURL.deletingLastPathComponent()

            // Build environment with PYTHONPATH for the dcmtag2table module
            var environment = pythonResolution.environment ?? ProcessInfo.processInfo.environment
            let existingPythonPath = environment["PYTHONPATH"]
            let scriptPath = scriptDirectory.path
            environment["PYTHONPATH"] = existingPythonPath.map { "\(scriptPath):\($0)" } ?? scriptPath

            let result = runPythonProcess(
                using: pythonResolution,
                arguments: scriptArguments,
                customEnvironment: environment
            )

            let combinedOutput = String(data: result.stdout + result.stderr, encoding: .utf8) ?? ""

            if let error = result.error {
                presentAlert(title: "dcmtag2table", message: "Python execution failed: \(error.localizedDescription)")
                return
            }

            if result.terminationStatus != 0 {
                let trimmed = combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
                let fallback = "Python script exited with status \(result.terminationStatus)."
                presentAlert(title: "dcmtag2table", message: trimmed.isEmpty ? fallback : trimmed)
                return
            }

            let summary = parsePythonSummary(combinedOutput)
            var message = "CSV generated successfully."
            if let csvPath = summary.csvPath, !csvPath.isEmpty {
                message = "CSV generated at:\n\(csvPath)"
            } else {
                message = "CSV generated in:\n\(outputDir.path)"
            }
            if let rowCount = summary.rowCount {
                message += "\nRows: \(rowCount)"
            }
            presentAlert(title: "dcmtag2table", message: message)
        } catch {
            presentAlert(title: "dcmtag2table", message: error.localizedDescription)
        }
    }

    private func buildManifestFile(in outputDir: URL) throws -> URL {
        guard let browser = BrowserController.currentBrowser() else {
            throw makeError("Unable to access the Horos database browser.")
        }

        // Get user's selection from the database browser (must be on main thread)
        let selection: [NSManagedObject]
        if Thread.isMainThread {
            selection = browser.databaseSelection() as? [NSManagedObject] ?? []
        } else {
            selection = DispatchQueue.main.sync {
                browser.databaseSelection() as? [NSManagedObject] ?? []
            }
        }
        
        var entries: [SeriesManifestEntry] = []
        var skippedSeries = 0
        var processedSeriesUIDs = Set<String>()

        if selection.isEmpty {
            // No selection: export entire database
            logToConsole("No selection in browser, exporting entire database...")
            guard let database = browser.database ?? DicomDatabase.activeLocal() else {
                throw makeError("Unable to access the Horos database.")
            }

            guard let studies = database.objects(forEntity: DicomDatabaseStudyEntityName) as? [DicomStudy] else {
                throw makeError("Unable to fetch studies from the Horos database.")
            }

            for study in studies {
                guard let seriesSet = study.series as? Set<DicomSeries> else { continue }
                for series in seriesSet {
                    if let entry = buildManifestEntry(for: series, study: study, processedUIDs: &processedSeriesUIDs) {
                        entries.append(entry)
                    } else {
                        skippedSeries += 1
                    }
                }
            }
        } else {
            // Process user's selection
            logToConsole("Processing \(selection.count) selected item(s) from browser...")
            for object in selection {
                if let study = object as? DicomStudy {
                    // Selected a study: include all its series
                    guard let seriesSet = study.series as? Set<DicomSeries> else { continue }
                    for series in seriesSet {
                        if let entry = buildManifestEntry(for: series, study: study, processedUIDs: &processedSeriesUIDs) {
                            entries.append(entry)
                        } else {
                            skippedSeries += 1
                        }
                    }
                } else if let series = object as? DicomSeries {
                    // Selected a series directly
                    let study = series.study
                    if let entry = buildManifestEntry(for: series, study: study, processedUIDs: &processedSeriesUIDs) {
                        entries.append(entry)
                    } else {
                        skippedSeries += 1
                    }
                } else if let image = object as? DicomImage {
                    // Selected an image: use its series
                    if let series = image.series {
                        let study = series.study
                        if let entry = buildManifestEntry(for: series, study: study, processedUIDs: &processedSeriesUIDs) {
                            entries.append(entry)
                        } else {
                            skippedSeries += 1
                        }
                    }
                }
            }
        }

        if skippedSeries > 0 {
            logToConsole("Skipped \(skippedSeries) series with no images or invalid paths.")
        }

        if entries.isEmpty {
            throw makeError("No valid series found to export. Please select studies or series in the database browser.")
        }

        let manifest = SeriesManifest(series: entries)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

        let data = try encoder.encode(manifest)
        let manifestURL = outputDir.appendingPathComponent("manifest_\(timestampString()).json")
        try data.write(to: manifestURL, options: .atomic)

        logToConsole("Manifest written to \(manifestURL.path) with \(entries.count) series.")
        return manifestURL
    }

    private func buildManifestEntry(for series: DicomSeries, study: DicomStudy?, processedUIDs: inout Set<String>) -> SeriesManifestEntry? {
        // Avoid duplicates
        if let uid = series.seriesInstanceUID, processedUIDs.contains(uid) {
            return nil
        }

        guard let image = representativeImage(for: series) else {
            return nil
        }

        guard let path = image.completePathResolved(), !path.isEmpty else {
            return nil
        }

        if let uid = series.seriesInstanceUID {
            processedUIDs.insert(uid)
        }

        return SeriesManifestEntry(
            filePath: path,
            studyInstanceUID: study?.studyInstanceUID,
            seriesInstanceUID: series.seriesInstanceUID
        )
    }

    private func representativeImage(for series: DicomSeries) -> DicomImage? {
        if let sorted = series.sortedImages() as? [DicomImage], let first = sorted.first {
            return first
        }

        if let images = series.images as? Set<DicomImage> {
            return images.first
        }

        return nil
    }

    private func ensureOutputDirectory() throws -> URL {
        let outputDir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("dcmtag2table-output")
        if !FileManager.default.fileExists(atPath: outputDir.path) {
            do {
                try FileManager.default.createDirectory(at: outputDir, withIntermediateDirectories: true)
            } catch {
                throw makeError("Unable to create output directory at \(outputDir.path).")
            }
        }
        return outputDir
    }

    private func resolveScriptURL() -> URL? {
        let bundle = Bundle(for: type(of: self))
        if let url = bundle.url(forResource: "main", withExtension: "py", subdirectory: "python_script") {
            return url
        }
        return bundle.url(forResource: "main", withExtension: "py")
    }

    private func parsePythonSummary(_ output: String) -> (csvPath: String?, rowCount: Int?) {
        var csvPath: String?
        var rowCount: Int?
        let lines = output.split(separator: "\n")
        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
            if trimmed.hasPrefix("CSV_OUTPUT=") {
                csvPath = String(trimmed.dropFirst("CSV_OUTPUT=".count))
            } else if trimmed.hasPrefix("ROW_COUNT=") {
                rowCount = Int(trimmed.dropFirst("ROW_COUNT=".count))
            }
        }
        return (csvPath, rowCount)
    }

    private func presentAlert(title: String, message: String) {
        if !Thread.isMainThread {
            DispatchQueue.main.async { [weak self] in
                self?.presentAlert(title: title, message: message)
            }
            return
        }

        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.alertStyle = .informational

        if let browserWindow = BrowserController.currentBrowser()?.window {
            alert.beginSheetModal(for: browserWindow, completionHandler: nil)
        } else {
            alert.runModal()
        }
    }

    private func logToConsole(_ message: String) {
        let trimmed = message.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        NSLog("[dcmtag2table] %@", trimmed)
    }

    private func timestampString() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd_HHmmss"
        return formatter.string(from: Date())
    }

    private func makeError(_ message: String) -> NSError {
        return NSError(domain: "dcmtag2table", code: 1, userInfo: [NSLocalizedDescriptionKey: message])
    }

    // MARK: - Managed Python Environment

    private func managedEnvironmentDirectory() -> URL? {
        let fileManager = FileManager.default
        guard let supportDirectory = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
            return nil
        }

        let pluginDirectory = supportDirectory.appendingPathComponent("dcmtag2tableHorosPlugin", isDirectory: true)
        let environmentDirectory = pluginDirectory.appendingPathComponent("PythonEnvironment", isDirectory: true)

        do {
            try fileManager.createDirectory(at: environmentDirectory, withIntermediateDirectories: true)
        } catch {
            logToConsole("Failed to create managed environment directory: \(error.localizedDescription)")
            return nil
        }

        return environmentDirectory
    }

    private func resolvePythonInterpreter() -> ExecutableResolution {
        // First try managed venv
        if let venvResolution = resolveManagedVenvPython() {
            return venvResolution
        }

        // Fallback to system python3
        return (
            URL(fileURLWithPath: "/usr/bin/env"),
            ["python3"],
            nil
        )
    }

    private func resolveManagedVenvPython() -> ExecutableResolution? {
        guard let environmentDirectory = managedEnvironmentDirectory() else {
            return nil
        }

        let binDirectory = environmentDirectory.appendingPathComponent("bin", isDirectory: true)
        let python3URL = binDirectory.appendingPathComponent("python3", isDirectory: false)
        let pythonURL = binDirectory.appendingPathComponent("python", isDirectory: false)
        let fileManager = FileManager.default

        let pythonBinary: URL
        if fileManager.isExecutableFile(atPath: python3URL.path) {
            pythonBinary = python3URL
        } else if fileManager.isExecutableFile(atPath: pythonURL.path) {
            pythonBinary = pythonURL
        } else {
            return nil
        }

        var environment: [String: String] = [:]
        var existingPath = ProcessInfo.processInfo.environment["PATH"] ?? ""
        let binPath = binDirectory.path
        let pathComponents = existingPath.split(separator: ":").map(String.init)
        if !pathComponents.contains(binPath) {
            existingPath = binPath + (existingPath.isEmpty ? "" : ":" + existingPath)
        }
        environment["PATH"] = existingPath
        environment["VIRTUAL_ENV"] = environmentDirectory.path

        return (pythonBinary, [], environment)
    }

    private func pythonModuleAvailable(_ moduleName: String, using resolution: ExecutableResolution) -> Bool {
        let script = """
import importlib.util
import sys

module = sys.argv[1]
spec = importlib.util.find_spec(module)
sys.exit(0 if spec is not None else 1)
"""

        let result = runPythonProcess(
            using: resolution,
            arguments: ["-c", script, moduleName]
        )

        if let error = result.error {
            logToConsole("Python execution failed while probing module '\(moduleName)': \(error.localizedDescription)")
            return false
        }

        return result.terminationStatus == 0
    }

    private func runPythonProcess(
        using resolution: ExecutableResolution,
        arguments: [String],
        customEnvironment: [String: String]? = nil
    ) -> ProcessExecutionResult {
        let process = Process()
        process.executableURL = resolution.executableURL
        process.arguments = resolution.leadingArguments + arguments

        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONUNBUFFERED"] = "1"

        if let baseEnvironment = resolution.environment {
            environment.merge(baseEnvironment) { _, new in new }
        }

        if let custom = customEnvironment {
            environment.merge(custom) { _, new in new }
        }

        process.environment = environment

        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        var capturedStdout = Data()
        var capturedStderr = Data()

        let stdoutHandle = stdoutPipe.fileHandleForReading
        let stderrHandle = stderrPipe.fileHandleForReading

        stdoutHandle.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            capturedStdout.append(data)

            if let message = String(data: data, encoding: .utf8), !message.isEmpty {
                self?.logToConsole(message)
            }
        }

        stderrHandle.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            capturedStderr.append(data)

            if let message = String(data: data, encoding: .utf8), !message.isEmpty {
                self?.logToConsole(message)
            }
        }

        var launchError: Error?
        do {
            try process.run()
        } catch {
            launchError = error
        }

        if let error = launchError {
            stdoutHandle.readabilityHandler = nil
            stderrHandle.readabilityHandler = nil
            return ProcessExecutionResult(terminationStatus: -1, stdout: capturedStdout, stderr: capturedStderr, error: error)
        }

        process.waitUntilExit()

        stdoutHandle.readabilityHandler = nil
        stderrHandle.readabilityHandler = nil

        capturedStdout.append(stdoutHandle.readDataToEndOfFile())
        capturedStderr.append(stderrHandle.readDataToEndOfFile())

        return ProcessExecutionResult(
            terminationStatus: process.terminationStatus,
            stdout: capturedStdout,
            stderr: capturedStderr,
            error: nil
        )
    }

    private func bootstrapManagedPythonEnvironment() -> ExecutableResolution? {
        guard let environmentDirectory = managedEnvironmentDirectory() else {
            logToConsole("Failed to resolve a location for the managed Python environment.")
            return nil
        }

        let binDirectory = environmentDirectory.appendingPathComponent("bin", isDirectory: true)
        let python3URL = binDirectory.appendingPathComponent("python3", isDirectory: false)
        let pythonURL = binDirectory.appendingPathComponent("python", isDirectory: false)
        let fileManager = FileManager.default

        // Create venv if it doesn't exist
        if !fileManager.fileExists(atPath: python3URL.path) && !fileManager.fileExists(atPath: pythonURL.path) {
            logToConsole("Creating managed Python environment…")

            let baseResolution: ExecutableResolution = (
                URL(fileURLWithPath: "/usr/bin/env"),
                ["python3"],
                nil
            )

            let result = runPythonProcess(
                using: baseResolution,
                arguments: ["-m", "venv", environmentDirectory.path]
            )

            if result.terminationStatus != 0 || result.error != nil {
                logToConsole("Failed to create virtual environment: status=\(result.terminationStatus)")
                return nil
            }
        }

        let pythonBinary: URL
        if fileManager.isExecutableFile(atPath: python3URL.path) {
            pythonBinary = python3URL
        } else if fileManager.isExecutableFile(atPath: pythonURL.path) {
            pythonBinary = pythonURL
        } else {
            logToConsole("Managed Python environment exists but no executable interpreter was found.")
            return nil
        }

        var environment: [String: String] = [:]
        var existingPath = ProcessInfo.processInfo.environment["PATH"] ?? ""
        let binPath = binDirectory.path
        let pathComponents = existingPath.split(separator: ":").map(String.init)
        if !pathComponents.contains(binPath) {
            existingPath = binPath + (existingPath.isEmpty ? "" : ":" + existingPath)
        }
        environment["PATH"] = existingPath
        environment["VIRTUAL_ENV"] = environmentDirectory.path

        let managedResolution: ExecutableResolution = (pythonBinary, [], environment)

        // Install dependencies if pandas is not available
        if !pythonModuleAvailable("pandas", using: managedResolution) {
            logToConsole("Installing required Python packages into managed environment…")

            // Upgrade pip first
            _ = runPythonProcess(
                using: managedResolution,
                arguments: ["-m", "pip", "install", "--upgrade", "pip"]
            )

            // Install all required packages
            let installResult = runPythonProcess(
                using: managedResolution,
                arguments: ["-m", "pip", "install", "pydicom", "pandas", "tqdm", "joblib"]
            )

            if installResult.terminationStatus != 0 || installResult.error != nil {
                logToConsole("Failed to install Python packages into managed environment: status=\(installResult.terminationStatus)")
                return nil
            }
        }

        guard pythonModuleAvailable("pandas", using: managedResolution) else {
            logToConsole("Managed environment was created but pandas is still unavailable.")
            return nil
        }

        logToConsole("Managed Python environment ready at: \(pythonBinary.path)")
        return managedResolution
    }

    private func ensureManagedEnvironment() -> ExecutableResolution? {
        // Check if managed venv already has pandas
        if let existing = resolveManagedVenvPython(), pythonModuleAvailable("pandas", using: existing) {
            return existing
        }

        // Bootstrap or repair the environment
        return bootstrapManagedPythonEnvironment()
    }
}

extension Dcmtag2tablePlugin: NSMenuItemValidation {
    func validateMenuItem(_ menuItem: NSMenuItem) -> Bool {
        return true
    }
}
