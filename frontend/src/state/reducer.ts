import type { Scenario, Target, View } from "../data/types";
export interface State {
  view: View;
  scenarioId: string;
  forecastIndex: number;
  eventIndex: number;
  eventCount: number;
  round: number;
  playing: boolean;
  revealed: boolean;
  componentId: string | null;
  series: Target[];
  baseline: string;
  mask: string;
  contingency: string;
  stress: string;
  actionId: string | null;
  labTab: string;
}
export const initialState: State = {
  view: "Overview",
  scenarioId: "first-week",
  forecastIndex: 0,
  eventIndex: 0,
  eventCount: 0,
  round: 0,
  playing: false,
  revealed: false,
  componentId: null,
  series: ["demand", "solar", "wind", "net_load"],
  baseline: "persistence",
  mask: "short-gap",
  contingency: "illustrative14:line:04",
  stress: "moderate",
  actionId: null,
  labTab: "Reconstruction",
};
export type StateAction =
  | { type: "view"; view: View }
  | { type: "scenario"; scenario: Scenario }
  | { type: "reset"; scenario: Scenario }
  | { type: "step"; index: number }
  | { type: "patch"; patch: Partial<State> }
  | { type: "contingency"; id: string }
  | { type: "stress"; value: string };
export function reducer(s: State, a: StateAction): State {
  switch (a.type) {
    case "view":
      return { ...s, view: a.view, playing: false };
    case "scenario":
    case "reset":
      return {
        ...initialState,
        view: s.view,
        scenarioId: a.scenario.id,
        forecastIndex: a.scenario.forecast_start,
      };
    case "step":
      return s.view === "Scenario laboratory"
        ? { ...s, round: a.index, actionId: null }
        : s.view === "Event diagnosis"
          ? { ...s, eventIndex: a.index }
          : { ...s, forecastIndex: a.index, revealed: false };
    case "contingency":
      return {
        ...s,
        contingency: a.id,
        round: 0,
        actionId: null,
        playing: false,
      };
    case "stress":
      return {
        ...s,
        stress: a.value,
        round: 0,
        actionId: null,
        playing: false,
      };
    case "patch":
      return { ...s, ...a.patch };
  }
}
