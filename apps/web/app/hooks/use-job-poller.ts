export type PollResult<T> = {
  status: string;
  succeeded: boolean;
  failed: boolean;
  data?: T;
  error?: string;
};

export function pollJob<T>(
  fetchStatus: () => Promise<PollResult<T>>,
  options: {
    intervalMs: number;
    timeoutMs: number;
    onTimeout: () => void;
    onSucceeded: (data: T) => void;
    onFailed: (error: string) => void;
  },
): void {
  const startTime = Date.now();

  const poll = async () => {
    if (Date.now() - startTime > options.timeoutMs) {
      options.onTimeout();
      return;
    }
    try {
      const result = await fetchStatus();
      if (result.succeeded && result.data !== undefined) {
        options.onSucceeded(result.data);
      } else if (result.failed) {
        options.onFailed(result.error ?? "Job failed");
      } else {
        setTimeout(poll, options.intervalMs);
      }
    } catch (error) {
      options.onFailed(error instanceof Error ? error.message : "Polling failed");
    }
  };

  setTimeout(poll, options.intervalMs);
}
