// render <MessageSkeleton /> and <DocumentCardSkeleton />
"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";

interface FallbackProps {
  error: Error;
  reset: () => void;
  label?: string;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (props: FallbackProps) => ReactNode;
  onError?: (error: Error, info: ErrorInfo) => void;
  label?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);

    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(
    error: Error
  ): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary] Caught error:", error);
    console.error(
      "[ErrorBoundary] Component stack:",
      info.componentStack
    );

    this.props.onError?.(error, info);
  }

  reset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      const fallbackProps: FallbackProps = {
        error: this.state.error,
        reset: this.reset,
        label: this.props.label,
      };

      if (this.props.fallback) {
        return this.props.fallback(fallbackProps);
      }

      return (
        <div className="flex min-h-[300px] items-center justify-center p-6">
          <div className="max-w-md rounded-xl border bg-white p-6 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">
              Something went wrong
            </h2>

            <p className="mb-4 text-sm text-gray-600">
              {this.state.error.message}
            </p>

            <button
              onClick={this.reset}
              className="rounded-lg border px-4 py-2 text-sm hover:bg-gray-50"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;