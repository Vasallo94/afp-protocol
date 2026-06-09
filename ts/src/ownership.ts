/** Anti-spoofing ownership verification (SPEC §7.3). */
import { schemeOf } from "./identity.js";

function stripAfter(s: string, ch: string): string {
  const i = s.indexOf(ch);
  return i === -1 ? s : s.slice(0, i);
}

/** PURL owned base: no `#fragment` (sub-tool), no `@version`. */
function purlBase(uri: string): string {
  const noFragment = stripAfter(uri, "#");
  return stripAfter(noFragment, "@");
}

/** Minimal urlsplit equivalent: authority + path, ignoring query/fragment. */
function splitUrl(uri: string): { netloc: string; path: string } {
  const afterScheme = uri.slice(uri.indexOf("://") + 3);
  const rest = stripAfter(stripAfter(afterScheme, "#"), "?");
  const slash = rest.indexOf("/");
  if (slash === -1) return { netloc: rest, path: "" };
  return { netloc: rest.slice(0, slash), path: rest.slice(slash) };
}

function segments(path: string): string[] {
  return path.split("/").filter((p) => p.length > 0);
}

/**
 * Does the report's subject fall under the subject the manifest declares?
 * Checks OWNERSHIP, not literal equality, per scheme:
 * - PURL: same package base (`@version`/`#fragment` don't change the owner).
 * - http(s)/mcp: same scheme, same authority (exact, case-insensitive), and
 *   the report path is the manifest path or a per-segment sub-path.
 * - others (e.g. `afp:`): equality after stripping `#fragment`.
 */
export function subjectIsOwnedBy(
  reportSubject: string | null | undefined,
  manifestSubject: string | null | undefined,
): boolean {
  if (!reportSubject || !manifestSubject) return false;
  const rScheme = schemeOf(reportSubject);
  const mScheme = schemeOf(manifestSubject);
  if (rScheme !== mScheme) return false;
  if (rScheme === "pkg") {
    return purlBase(reportSubject) === purlBase(manifestSubject);
  }
  if (rScheme === "http" || rScheme === "https" || rScheme === "mcp") {
    const r = splitUrl(reportSubject);
    const m = splitUrl(manifestSubject);
    if (r.netloc.toLowerCase() !== m.netloc.toLowerCase()) return false;
    const rSeg = segments(r.path);
    const mSeg = segments(m.path);
    return mSeg.every((seg, i) => rSeg[i] === seg);
  }
  return stripAfter(reportSubject, "#") === stripAfter(manifestSubject, "#");
}
