/** One paragraph of narration: what labels it in the editor and its spoken text. */
export type Paragraph = { label: string; text: string }

/**
 * One draft under review: the file it came from, its paragraphs as written,
 * and what นน's script_edit.md holds now. `texts[i]` pairs with `base[i]`.
 */
export type Review = {
  episodeDir: string
  file: string
  mdPath: string
  base: Paragraph[]
  texts: string[]
  mdMtimeMs: number
  status: 'editing' | 'sent'
  /** The `_nn` file the edits were saved as, once sent. */
  sentAs?: string
  /** Why script_edit.md cannot be read back: a heading lost, doubled or moved. */
  error?: string
  /** A newer draft the model wrote while นน still had edits unsent. */
  newer?: string
}

export type View = { showAll: boolean; editing: number | null }

declare module 'claude-code' {
  interface PluginState {
    'mp-script': {
      review: Review | null
      /** When the session first started: drafts older than this were never this session's. */
      since: number
      /** Each draft path handled, by the mtime it was handled at. */
      seen: Record<string, number>
      view: View
    }
  }
}
