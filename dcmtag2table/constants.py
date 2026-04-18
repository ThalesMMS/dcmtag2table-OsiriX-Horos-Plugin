non_phi_ct_dicom_tags = [  # These are required tags for CT. Make sure to change this when working with other modalities (MR, CR, US)
    "PixelData",
    "SeriesNumber",  # Number of the series within the study
    "AcquisitionNumber",  # Number identifying the single continuous gathering of data
    "InstanceNumber",  # Number identifying the image
    "Modality",  # Type of equipment that created the image (CT for computed tomography)
    "Manufacturer",  # Manufacturer of the equipment
    "SliceThickness",  # Thickness of the slice in mm
    "SpacingBetweenSlices",  # the distance between two adjacent slices in millimeters, measured from the center of each slice to the center of the other slice
    "KVP",  # Peak kilovoltage output of the X-ray tube used
    "DataCollectionDiameter",  # Diameter of the region from which data were collected
    "SoftwareVersions",  # Software versions of the equipment
    "ReconstructionDiameter",  # Diameter within which the reconstruction is performed
    "GantryDetectorTilt",  # Tilt of gantry with respect to the table
    "TableHeight",  # Height of the table
    "RotationDirection",  # Direction of rotation of the source around the patient (CW or CCW)
    "ExposureTime",  # Time of X-ray exposure in ms
    "XRayTubeCurrent",  # X-ray tube current in mA
    "Exposure",  # Dose area product in mGy*cm²
    "FilterType",  # Type of filter used
    "GeneratorPower",  # Power of the generator used to make the exposure in kW
    "FocalSpots",  # Size of the focal spot in mm
    "ConvolutionKernel",  # Description of the convolution kernel or kernels used for the reconstruction
    "PatientPosition",  # Position of the patient relative to the imaging equipment space
    "SliceLocation",  # Location of the slice
    "ImagePositionPatient",  # Position of the image frame in patient coordinates
    "ImageOrientationPatient",  # Orientation of the image frame in patient coordinates
    "SamplesPerPixel",  # Number of samples (colors) in the image
    "PhotometricInterpretation",  # Photometric interpretation
    "Rows",  # Number of rows in the image
    "Columns",  # Number of columns in the image
    "PixelSpacing",  # Physical distance between the center of each pixel
    "BitsAllocated",  # Number of bits allocated for each pixel sample
    "BitsStored",  # Number of bits stored for each pixel sample
    "HighBit",  # Most significant bit for pixel sample data
    "PixelRepresentation",  # Data representation of the pixel samples
    "WindowCenter",  # Window center for display
    "WindowWidth",  # Window width for display
    "RescaleIntercept",  # Value to be added to the rescaled slope intercept
    "RescaleSlope",  # Slope for pixel value rescaling
]

required_mg_dicom_tags = [
    # General Series Module
    "Modality",
    "SeriesNumber",
    # General Equipment Module
    "Manufacturer",
    # General Image Module
    "ImageType",
    "InstanceNumber",
    "AcquisitionNumber",
    "SeriesDescription",
    "StudyDescription",
    # Image Pixel Module
    "SamplesPerPixel",
    "PhotometricInterpretation",
    "Rows",
    "Columns",
    "BitsAllocated",
    "BitsStored",
    "HighBit",
    "PixelRepresentation",
    "PixelData",
    # -- DX Image Module
    "KVP",
    "DistanceSourceToDetector",
    "ExposureTime",
    "XRayTubeCurrent",
    "Exposure",
    "CassetteOrientation",
    "CassetteSize",
    "ExposuresOnPlate",
    # -- Mammography Image Module
    "BodyPartExamined",
    "PixelSpacing",
    "FilterMaterial",
    "FilterType",
    "CompressionForce",
    "ViewPosition",
    "PatientOrientation",
    "PresentationLUTShape",
    # -- Newly added items from fields that were missing:
    "EstimatedRadiographicMagnificationFactor",
    "ImagerPixelSpacing",
    "Grid",
    "FocalSpots",
    "AnodeTargetMaterial",
    "BodyPartThickness",
    "PositionerType",
    "PositionerPrimaryAngle",
    "DetectorConditionsNominalFlag",
    "DetectorTemperature",
    "DetectorType",
    "DetectorID",
    "ImageLaterality",
    "PixelPaddingValue",
    "QualityControlImage",
    "BurnedInAnnotation",
    "PixelIntensityRelationship",
    "PixelIntensityRelationshipSign",
    "WindowCenter",
    "WindowWidth",
    "RescaleIntercept",
    "RescaleSlope",
    "RescaleType",
    "LossyImageCompression",
    "Sensitivity",
    "AcquisitionDeviceProcessingCode",
    "ImagesInAcquisition",
    "BreastImplantPresent",
    "RelativeXRayExposure",
    "SpecificCharacterSet",
    "DetectorConfiguration",
    "DetectorDescription",
    "SOPClassUID",
    "ManufacturerModelName",
    "DistanceSourceToPatient",
    "PositionerSecondaryAngle",
    "DetectorActiveShape",
    "DetectorActiveDimensions",
    "FieldOfViewOrigin",
    "FieldOfViewRotation",
    "FieldOfViewHorizontalFlip",
    "PixelAspectRatio",
    "FieldOfViewShape",
    "GridPeriod",
    "PartialView",
    "PartialViewDescription",
    "FilterThicknessMinimum",
    "ExposureInuAs",  # (0018, 1153)
    "FilterThicknessMaximum",
    "ExposureControlMode",
    "Laterality",
    "ExposureControlModeDescription",
    "ExposureStatus",
    "EthnicGroup",
]
