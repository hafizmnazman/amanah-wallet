/** USDC amounts. On-chain values are base units with 6 decimals; the API's amount_usdc fields are whole USDC. */
export const USDC_DECIMALS = 6;
const SCALE = 10n ** BigInt(USDC_DECIMALS);

function group(digits: string): string {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** Formats base units: 1200000000n becomes "1,200.00". Keeps up to 6 decimals when they are not zero. */
export function formatBaseUnits(value: bigint | string | number): string {
  const units = typeof value === "bigint" ? value : BigInt(value);
  const negative = units < 0n;
  const abs = negative ? -units : units;
  const whole = abs / SCALE;
  let fraction = (abs % SCALE).toString().padStart(USDC_DECIMALS, "0").replace(/0+$/, "");
  if (fraction.length < 2) fraction = fraction.padEnd(2, "0");
  return `${negative ? "-" : ""}${group(whole.toString())}.${fraction}`;
}

/** Parses a whole-USDC amount such as 150, "150.5" or "1,200.00" into base units, exactly. */
export function parseUsdc(value: number | string): bigint {
  const text = (typeof value === "number" ? value.toFixed(USDC_DECIMALS) : value).replace(/,/g, "").trim();
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(text);
  if (!match) throw new Error(`not a USDC amount: ${value}`);
  const [, sign, whole, fraction = ""] = match;
  if (fraction.length > USDC_DECIMALS && /[1-9]/.test(fraction.slice(USDC_DECIMALS))) {
    throw new Error(`more than ${USDC_DECIMALS} decimals: ${value}`);
  }
  const units = BigInt(whole) * SCALE + BigInt(fraction.slice(0, USDC_DECIMALS).padEnd(USDC_DECIMALS, "0"));
  return sign === "-" ? -units : units;
}

/** Formats a whole-USDC amount from the API: 150 becomes "150.00". */
export function formatUsdc(value: number | string): string {
  return formatBaseUnits(parseUsdc(value));
}

/** A total the usage report may hide: "1,650.00 USDC", or the given words when it is null. */
export function formatTotal(value: number | string | null, hidden = "not shown"): string {
  return value === null ? hidden : `${formatUsdc(value)} USDC`;
}
