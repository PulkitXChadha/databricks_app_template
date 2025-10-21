/**
 * Usage Tracker Service
 * 
 * Batches usage events and submits them to the backend automatically.
 * 
 * Features:
 * - Automatic batching (10 seconds OR 20 events, whichever occurs first)
 * - Race condition handling for simultaneous timer/count triggers
 * - Client-side exponential backoff retry (1s, 2s delays; 3 attempts max)
 * - Debouncing for high-frequency events
 * - navigator.sendBeacon for page unload
 */

import { MetricsService } from '../fastapi_client';

interface UsageEvent {
  event_type: string;
  page_name?: string;
  element_id?: string;
  success?: boolean;
  metadata?: Record<string, any>;
  timestamp: string;
}

interface UsageEventBatchRequest {
  events: UsageEvent[];
}

class UsageTracker {
  private eventQueue: UsageEvent[] = [];
  private batchSize = 20;
  private batchInterval = 10000; // 10 seconds
  private timerId: NodeJS.Timeout | null = null;
  private flushInProgress = false; // Mutex flag for race condition handling

  constructor() {
    this.startBatchTimer();
    
    // Flush queue on page unload using sendBeacon
    window.addEventListener('beforeunload', () => {
      this.flushWithSendBeacon();
    });
  }

  /**
   * Track a usage event.
   * 
   * Events are queued and automatically submitted when:
   * - 20 events accumulated (batch size)
   * - 10 seconds elapsed (batch interval)
   * - Page unload (beforeunload event)
   * 
   * @param event Usage event data (timestamp added automatically)
   */
  track(event: Omit<UsageEvent, 'timestamp'>) {
    const fullEvent: UsageEvent = {
      ...event,
      timestamp: new Date().toISOString()
    };
    
    this.eventQueue.push(fullEvent);
    
    // T077: Race condition handling - clear timer when count reaches 20
    if (this.eventQueue.length >= this.batchSize) {
      if (this.timerId) {
        clearTimeout(this.timerId);
        this.timerId = null;
      }
      this.flush();
    }
  }

  /**
   * Manually flush the event queue immediately.
   * Uses mutex flag to prevent duplicate flushes from race conditions.
   */
  flush() {
    // T077: Race condition protection with mutex flag
    if (this.flushInProgress) {
      console.debug('[UsageTracker] Flush already in progress, skipping duplicate');
      return;
    }
    
    if (this.eventQueue.length === 0) {
      return;
    }
    
    this.flushInProgress = true;
    const batch = this.eventQueue.splice(0); // Remove all events from queue
    
    // T083: Client-side exponential backoff retry
    this.submitWithRetry(batch)
      .finally(() => {
        this.flushInProgress = false;
        // Reset timer after flush completion
        this.startBatchTimer();
      });
  }

  /**
   * Submit batch with exponential backoff retry.
   * 
   * T083: Retry logic:
   * - Initial delay: 1 second
   * - Backoff multiplier: 2x
   * - Max attempts: 3 total
   * - Delays: 1s after 1st failure, 2s after 2nd failure
   * - After 3 failures: log error and discard batch
   */
  private async submitWithRetry(batch: UsageEvent[], attempt: number = 1): Promise<void> {
    try {
      await MetricsService.submitUsageEvents({
        events: batch
      });
      
      console.debug(`[UsageTracker] Successfully submitted ${batch.length} events`);
      
    } catch (error) {
      console.error(`[UsageTracker] Batch submission failed (attempt ${attempt}/3):`, error);
      
      if (attempt >= 3) {
        // T083: After 3 attempts, discard batch to prevent memory accumulation
        console.error(
          `[UsageTracker] Failed to submit usage events after 3 attempts. ` +
          `Discarding ${batch.length} events to prevent memory accumulation.`
        );
        return;
      }
      
      // T083: Exponential backoff delays (1s, 2s)
      const delayMs = attempt === 1 ? 1000 : 2000;
      
      console.debug(`[UsageTracker] Retrying in ${delayMs}ms...`);
      
      await new Promise(resolve => setTimeout(resolve, delayMs));
      
      // Retry with incremented attempt counter
      return this.submitWithRetry(batch, attempt + 1);
    }
  }

  /**
   * Flush queue using navigator.sendBeacon for page unload.
   * 
   * T082: sendBeacon is synchronous and not cancelable by browser,
   * ensuring events are sent even during navigation/page close.
   * 
   * Backend MUST accept both Content-Type: application/json and text/plain.
   */
  private flushWithSendBeacon() {
    if (this.eventQueue.length === 0) {
      return;
    }
    
    const batch = this.eventQueue.splice(0);
    const payload = JSON.stringify({ events: batch });
    
    // Get auth token from request headers (if available)
    // Note: sendBeacon may not include custom headers in some browsers
    const url = '/api/v1/metrics/usage-events';
    
    try {
      const sent = navigator.sendBeacon(url, payload);
      
      if (sent) {
        console.debug(`[UsageTracker] Sent ${batch.length} events via sendBeacon on page unload`);
      } else {
        console.warn(`[UsageTracker] sendBeacon failed, ${batch.length} events may be lost`);
      }
    } catch (error) {
      console.error('[UsageTracker] sendBeacon error:', error);
      // T082: Acceptable data loss during aggressive browser crashes
      // Maximum acceptable loss rate: <0.1% measured over 7-day period
    }
  }

  /**
   * Start the batch timer (10 seconds).
   * Automatically flushes queue when timer expires.
   */
  private startBatchTimer() {
    // Clear existing timer if any
    if (this.timerId) {
      clearTimeout(this.timerId);
    }
    
    this.timerId = setTimeout(() => {
      // T077: Check mutex flag to prevent duplicate flush
      if (!this.flushInProgress && this.eventQueue.length > 0) {
        this.flush();
      }
    }, this.batchInterval);
  }
}

// Singleton instance
export const usageTracker = new UsageTracker();


/**
 * T084: Debounce helper for high-frequency events.
 * 
 * Use for typing, scrolling, window resizing - NOT for discrete actions
 * like button clicks or form submissions.
 * 
 * Delay: 500ms per spec.md edge cases
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delayMs: number = 500
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null;
  
  return function(this: any, ...args: Parameters<T>) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    
    timeoutId = setTimeout(() => {
      fn.apply(this, args);
    }, delayMs);
  };
}


/**
 * T080: Get element identifier using hybrid strategy.
 * 
 * Priority:
 * 1. data-track-id attribute (explicit tracking identifier)
 * 2. HTML id attribute (if data-track-id absent)
 * 3. Fallback: `${tagName}.${textContent}` (e.g., "button.Submit Query")
 * 
 * Truncated to 100 characters per FR-010.
 */
export function getElementIdentifier(element: HTMLElement): string {
  // 1. Check data-track-id attribute
  const trackId = element.getAttribute('data-track-id');
  if (trackId) {
    return trackId.substring(0, 100);
  }
  
  // 2. Check HTML id attribute
  if (element.id) {
    return element.id.substring(0, 100);
  }
  
  // 3. Fallback: tagName.textContent
  const tagName = element.tagName.toLowerCase();
  const textContent = element.textContent?.trim() || '';
  const fallback = `${tagName}.${textContent}`;
  
  return fallback.substring(0, 100);
}

