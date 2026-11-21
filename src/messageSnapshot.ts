import type { Message } from './types';

/** Keep one immutable history reference while capture-only snapshots arrive. */
export class MessageSnapshotCache {
  private session = '';
  private signature = '';
  private messages: Message[] = [];

  accept(session: string, messages: Message[]): Message[] {
    // Compare every serialized field, including corrections and alternatives.
    // Cache only the latest history; never retain prior sessions or snapshots.
    const signature = JSON.stringify(messages);
    if (session !== this.session || signature !== this.signature) {
      this.session = session;
      this.signature = signature;
      this.messages = messages;
    }
    return this.messages;
  }
}
