import { StrictMode, Component, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import "./styles/main.css";
import "./styles/layout.css";
import "./styles/overview.css";
class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: string }
> {
  state = { error: "" };
  static getDerivedStateFromError(error: Error) {
    return { error: error.message };
  }
  render() {
    return this.state.error ? (
      <main className="boot">
        <h1>Dashboard unavailable</h1>
        <p role="alert">{this.state.error}</p>
        <button onClick={() => location.reload()}>Reload dashboard</button>
        <p>No simulated output is substituted for missing model evidence.</p>
      </main>
    ) : (
      this.props.children
    );
  }
}
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
