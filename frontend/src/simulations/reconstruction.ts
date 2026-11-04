export function reconstruct(
  trace: { step: number; reference: number }[],
  steps: number[],
  equipment: "in_service" | "out_of_service" | "unknown",
) {
  const hidden = new Set(steps);
  return trace.map((row, index) => {
    let reconstructed: number | null = null;
    if (hidden.has(row.step) && equipment === "in_service") {
      let left = index - 1,
        right = index + 1;
      while (left >= 0 && hidden.has(trace[left].step)) left--;
      while (right < trace.length && hidden.has(trace[right].step)) right++;
      if (left >= 0 && right < trace.length)
        reconstructed =
          trace[left].reference +
          ((trace[right].reference - trace[left].reference) * (index - left)) /
            (right - left);
    }
    return {
      ...row,
      observed: hidden.has(row.step) ? null : row.reference,
      reconstructed,
      missing: hidden.has(row.step),
    };
  });
}
