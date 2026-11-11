export interface CharCountState {
  count: number;
  remaining: number;
  over: boolean;
  /** True when the text is empty or only whitespace. */
  empty: boolean;
}

export function charCountState(text: string, max: number): CharCountState {
  const count = text.length;
  return {
    count,
    remaining: max - count,
    over: count > max,
    empty: text.trim().length === 0,
  };
}
