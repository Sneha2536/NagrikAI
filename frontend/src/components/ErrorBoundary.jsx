/**
 * ErrorBoundary.jsx: if any page crashes, show a friendly message instead of a blank screen.
 * (React only supports this as a class component.)
 */
import { Component } from "react";
import StateMessage from "./StateMessage.jsx";

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Page crashed:", error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <StateMessage
        title="Something went wrong on this page"
        text={String(this.state.error.message || this.state.error)}
        onRetry={() => window.location.reload()}
      />
    );
  }
}
