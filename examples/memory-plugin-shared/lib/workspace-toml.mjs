/**
 * Zero-dependency subset TOML parser for `.openviking.toml` workspace configs.
 *
 * Intentionally excludes `${VAR}` expansion and arbitrary code execution so a
 * repository-committed `.openviking.toml` obeys the exact same safety model as
 * `.openviking/config.json`.
 */

function stripTomlComment(line) {
  let quote = "";
  let escaped = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (ch === "\\" && quote === "\"") {
      escaped = true;
      continue;
    }
    if (ch === "\"" || ch === "'") {
      quote = quote === ch ? "" : (quote || ch);
      continue;
    }
    if (ch === "#" && !quote) return line.slice(0, i);
  }
  return line;
}

function splitTopLevelItems(raw) {
  const items = [];
  let cur = "";
  let quote = "";
  let escaped = false;
  for (let i = 0; i < raw.length; i += 1) {
    const ch = raw[i];
    if (escaped) {
      cur += ch;
      escaped = false;
      continue;
    }
    if (ch === "\\" && quote === "\"") {
      cur += ch;
      escaped = true;
      continue;
    }
    if (ch === "\"" || ch === "'") {
      quote = quote === ch ? "" : (quote || ch);
      cur += ch;
      continue;
    }
    if (ch === "," && !quote) {
      if (cur.trim()) items.push(cur.trim());
      cur = "";
      continue;
    }
    cur += ch;
  }
  if (cur.trim()) items.push(cur.trim());
  return items;
}

function parseTomlValue(raw) {
  const val = String(raw || "").trim();
  if (val === "true") return true;
  if (val === "false") return false;
  if ((val.startsWith("\"") && val.endsWith("\"")) || (val.startsWith("'") && val.endsWith("'"))) {
    const inner = val.slice(1, -1);
    return val.startsWith("\"") ? inner.replace(/\\"/g, "\"").replace(/\\\\/g, "\\") : inner;
  }
  if (val.startsWith("[") && val.endsWith("]")) {
    const inner = val.slice(1, -1).trim();
    return inner ? splitTopLevelItems(inner).map(parseTomlValue) : [];
  }
  if (/^[+-]?\d+$/.test(val)) return Number.parseInt(val, 10);
  if (/^[+-]?\d+\.\d+$/.test(val)) return Number.parseFloat(val);
  throw new SyntaxError(`Unsupported TOML value: ${val}`);
}

export function parseWorkspaceToml(text) {
  const root = Object.create(null);
  let target = root;
  const lines = String(text || "").split(/\r?\n/);

  for (let i = 0; i < lines.length; i += 1) {
    const cleaned = stripTomlComment(lines[i]).trim();
    if (!cleaned) continue;

    const section = /^\[([a-zA-Z0-9_.-]+)\]$/.exec(cleaned);
    if (section) {
      let node = root;
      for (const part of section[1].split(".")) {
        if (part === "__proto__" || part === "constructor" || part === "prototype") {
          node = null;
          break;
        }
        if (!node[part] || typeof node[part] !== "object" || Array.isArray(node[part])) {
          node[part] = Object.create(null);
        }
        node = node[part];
      }
      target = node || Object.create(null);
      continue;
    }

    const eq = cleaned.indexOf("=");
    if (eq === -1) throw new SyntaxError(`Invalid TOML line ${i + 1}: ${cleaned}`);
    const key = cleaned.slice(0, eq).trim().replace(/^["']|["']$/g, "");
    let rhs = cleaned.slice(eq + 1).trim();
    while (rhs.startsWith("[") && !rhs.endsWith("]") && i + 1 < lines.length) {
      i += 1;
      rhs += ` ${stripTomlComment(lines[i]).trim()}`;
    }
    const parsedVal = parseTomlValue(rhs);
    Object.defineProperty(target, key, {
      value: parsedVal,
      enumerable: true,
      writable: true,
      configurable: true,
    });
  }
  return root;
}
