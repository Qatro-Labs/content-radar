import { describe, expect, it } from 'vitest'

import { createSseParser, type SseMessage } from '../sse'

function collect() {
  const messages: SseMessage[] = []
  const parser = createSseParser((message) => messages.push(message))
  return { messages, parser }
}

describe('createSseParser', () => {
  it('joins a message split across several chunks', () => {
    const { messages, parser } = collect()

    parser.push('event: st')
    parser.push('ep\ndata: {"id": 1}\n')
    parser.push('\n')

    expect(messages).toEqual([{ event: 'step', data: '{"id": 1}' }])
  })

  it('splits two messages that arrive in one chunk', () => {
    const { messages, parser } = collect()

    parser.push('event: step\ndata: 1\n\nevent: done\ndata: 2\n\n')

    expect(messages).toEqual([
      { event: 'step', data: '1' },
      { event: 'done', data: '2' },
    ])
  })

  it('accepts CRLF line endings, even split between chunks', () => {
    const { messages, parser } = collect()

    parser.push('event: answer\r\ndata: hola\r')
    parser.push('\n\r\n')

    expect(messages).toEqual([{ event: 'answer', data: 'hola' }])
  })

  it('ignores the keep-alive comment', () => {
    const { messages, parser } = collect()

    parser.push(': ping\n\nevent: done\ndata: {}\n\n')

    expect(messages).toEqual([{ event: 'done', data: '{}' }])
  })

  it('joins several data lines of one message with a newline', () => {
    const { messages, parser } = collect()

    parser.push('data: primera\ndata: segunda\n\n')

    expect(messages).toEqual([{ event: 'message', data: 'primera\nsegunda' }])
  })

  it('emits the last message on end when the stream has no trailing blank line', () => {
    const { messages, parser } = collect()

    parser.push('event: done\ndata: {"steps": 1}')
    expect(messages).toEqual([])

    parser.end()

    expect(messages).toEqual([{ event: 'done', data: '{"steps": 1}' }])
  })
})
