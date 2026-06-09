/** Error taxonomy mirroring the Python reference implementation. */

export class ReportInvalid extends Error {
  override name = "ReportInvalid";
}

export class ManifestInvalid extends Error {
  override name = "ManifestInvalid";
}

export class SecretDetected extends Error {
  override name = "SecretDetected";
}

export class InvalidSubjectUri extends Error {
  override name = "InvalidSubjectUri";
}
