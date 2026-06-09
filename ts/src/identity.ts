/** subject_uri validation (SPEC §5). */
import { PackageURL } from "packageurl-js";

import { InvalidSubjectUri } from "./errors.js";

export const SUPPORTED_SCHEMES = ["pkg", "https", "http", "mcp", "afp"] as const;

export function schemeOf(uri: string): string {
  const authority = uri.indexOf("://");
  if (authority !== -1) return uri.slice(0, authority);
  const colon = uri.indexOf(":");
  if (colon !== -1) return uri.slice(0, colon);
  return "";
}

export function validateSubjectUri(uri: unknown): string {
  if (typeof uri !== "string" || uri.length === 0) {
    throw new InvalidSubjectUri("empty subject_uri");
  }
  const scheme = schemeOf(uri);
  if (!(SUPPORTED_SCHEMES as readonly string[]).includes(scheme)) {
    throw new InvalidSubjectUri(`unsupported scheme: ${JSON.stringify(scheme)}`);
  }
  if (scheme === "pkg") {
    try {
      PackageURL.fromString(uri);
    } catch (exc) {
      throw new InvalidSubjectUri(`invalid PURL: ${(exc as Error).message}`);
    }
    return uri;
  }
  // http(s)/mcp/afp: the locator after the separator must be non-empty.
  const sep = uri.includes("://") ? "://" : ":";
  const rest = uri.slice(uri.indexOf(sep) + sep.length);
  if (rest.length === 0) {
    throw new InvalidSubjectUri(`empty locator for ${JSON.stringify(scheme)}`);
  }
  return uri;
}
