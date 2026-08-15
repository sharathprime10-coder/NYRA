import React, { Component, type ErrorInfo, type ReactNode } from "react";
import * as Sentry from "@sentry/react";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
  name?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`ErrorBoundary caught an error in ${this.props.name || 'Component'}:`, error, errorInfo);
    
    // Only capture exception if Sentry is initialized
    if (import.meta.env.VITE_SENTRY_DSN) {
      Sentry.captureException(error, { extra: { componentName: this.props.name } });
    }
  }

  private handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center p-8 m-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl shadow-2xl">
          <div className="w-16 h-16 mb-4 text-red-400">
            <svg xmlns="http://www.w3.org/.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Something went wrong</h2>
          <p className="text-white/60 text-center text-sm mb-6 max-w-md">
            {this.props.name 
              ? `The ${this.props.name} encountered an unexpected error.` 
              : "An unexpected error occurred while rendering this component."}
          </p>
          <button 
            onClick={this.handleReload}
            className="px-6 py-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-full text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Reload application
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
