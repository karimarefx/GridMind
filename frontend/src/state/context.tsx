import { createContext, useContext, type Dispatch } from "react";
import type { Bundle } from "../data/types";
import type { State, StateAction } from "./reducer";
export const DashboardContext = createContext<{
  data: Bundle;
  state: State;
  dispatch: Dispatch<StateAction>;
} | null>(null);
export function useDashboard() {
  const c = useContext(DashboardContext);
  if (!c) throw new Error("Dashboard provider missing");
  return c;
}
