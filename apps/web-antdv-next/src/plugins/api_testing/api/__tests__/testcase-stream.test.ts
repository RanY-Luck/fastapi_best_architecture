import { beforeEach, describe, expect, it, vi } from 'vitest';

import { executeTestCaseStream } from '../testcase';
import type { TestCaseStreamEvent } from '../types';

const textEncoder = new TextEncoder();
const fetchMock = vi.stubGlobal('fetch', vi.fn());

function streamFromChunks(chunks: string[]) {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(textEncoder.encode(chunk));
      }
      controller.close();
    },
  });
}

describe('testcase stream', () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  it('parses ndjson events and preserves unicode/newlines', async () => {
    const payload = [
      JSON.stringify({
        type: 'run_start',
        message: '开始\n测试',
        timestamp: '2026-03-31T00:00:00Z',
      }),
      JSON.stringify({
        type: 'run_end',
        report_id: 42,
      }),
    ]
      .map((line) => `${line}\n`)
      .join('');

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: streamFromChunks([payload]),
    });

    const events: TestCaseStreamEvent[] = [];
    for await (const event of executeTestCaseStream(1)) {
      events.push(event);
    }

    expect(events).toHaveLength(2);
    expect(events[0].message).toBe('开始\n测试');
    expect(events[1].report_id).toBe(42);
  });

  it('throws when stream terminates with an error event', async () => {
    const payload = [
      JSON.stringify({ type: 'run_start' }),
      JSON.stringify({ type: 'error', message: 'boom 错误' }),
    ]
      .map((line) => `${line}\n`)
      .join('');

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: streamFromChunks([payload]),
    });

    await expect(async () => {
      for await (const event of executeTestCaseStream(2)) {
        expect(event).toBeDefined();
      }
    }).rejects.toThrow('boom 错误');
  });
});
