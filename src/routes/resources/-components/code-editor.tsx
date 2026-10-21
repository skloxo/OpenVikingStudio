import { useEffect, useMemo, useRef, useImperativeHandle, forwardRef } from 'react'
import { Compartment, EditorState } from '@codemirror/state'
import {
  EditorView,
  getDialog,
  keymap,
  lineNumbers,
  highlightActiveLine,
  highlightActiveLineGutter,
  drawSelection,
} from '@codemirror/view'
import {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
} from '@codemirror/commands'
import {
  syntaxHighlighting,
  defaultHighlightStyle,
  bracketMatching,
  foldGutter,
  indentOnInput,
} from '@codemirror/language'
import type { LanguageSupport } from '@codemirror/language'
import { searchKeymap, highlightSelectionMatches } from '@codemirror/search'
import {
  autocompletion,
  closeBrackets,
  closeBracketsKeymap,
} from '@codemirror/autocomplete'
import { oneDark } from '@codemirror/theme-one-dark'
import { useTranslation } from 'react-i18next'
import { editorPhrases } from '#/i18n/editor-phrases'

const languageLoaders: Partial<Record<string, () => Promise<LanguageSupport>>> =
  {
    javascript: () =>
      import('@codemirror/lang-javascript').then((m) =>
        m.javascript({ jsx: true, typescript: false }),
      ),
    typescript: () =>
      import('@codemirror/lang-javascript').then((m) =>
        m.javascript({ jsx: true, typescript: true }),
      ),
    python: () => import('@codemirror/lang-python').then((m) => m.python()),
    json: () => import('@codemirror/lang-json').then((m) => m.json()),
    html: () => import('@codemirror/lang-html').then((m) => m.html()),
    css: () => import('@codemirror/lang-css').then((m) => m.css()),
    markdown: () =>
      import('@codemirror/lang-markdown').then((m) => m.markdown()),
    rust: () => import('@codemirror/lang-rust').then((m) => m.rust()),
    cpp: () => import('@codemirror/lang-cpp').then((m) => m.cpp()),
    java: () => import('@codemirror/lang-java').then((m) => m.java()),
    sql: () => import('@codemirror/lang-sql').then((m) => m.sql()),
    xml: () => import('@codemirror/lang-xml').then((m) => m.xml()),
    yaml: () => import('@codemirror/lang-yaml').then((m) => m.yaml()),
  }

const extMap: Record<string, string> = {
  ts: 'typescript',
  tsx: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  py: 'python',
  pyw: 'python',
  rs: 'rust',
  c: 'cpp',
  h: 'cpp',
  cpp: 'cpp',
  cc: 'cpp',
  cxx: 'cpp',
  hpp: 'cpp',
  java: 'java',
  json: 'json',
  html: 'html',
  htm: 'html',
  svg: 'xml',
  xml: 'xml',
  css: 'css',
  scss: 'css',
  less: 'css',
  md: 'markdown',
  markdown: 'markdown',
  sql: 'sql',
  yml: 'yaml',
  yaml: 'yaml',
}

function detectLanguage(filename: string): string | null {
  const ext = filename.toLowerCase().split('.').pop() || ''
  return extMap[ext] || null
}

export interface CodeEditorHandle {
  getContent: () => string
}

interface CodeEditorProps {
  initialContent: string
  filename: string
  isDark?: boolean
  readOnly?: boolean
  ariaLabel?: string
  onChange?: (content: string) => void
}

export const CodeEditor = forwardRef<CodeEditorHandle, CodeEditorProps>(
  function CodeEditor(
    {
      initialContent,
      filename,
      isDark = false,
      readOnly = false,
      ariaLabel,
      onChange,
    },
    ref,
  ) {
    const { t } = useTranslation('studio')
    const phrases = useMemo(() => editorPhrases(t), [t])
    const phrasesRef = useRef(phrases)
    phrasesRef.current = phrases
    const phrasesCompartment = useRef(new Compartment())
    const attributesRef = useRef(ariaLabel)
    attributesRef.current = ariaLabel
    const attributesCompartment = useRef(new Compartment())
    const readOnlyCompartment = useRef(new Compartment())
    const containerRef = useRef<HTMLDivElement>(null)
    const viewRef = useRef<EditorView | null>(null)

    useImperativeHandle(ref, () => ({
      getContent: () => viewRef.current?.state.doc.toString() ?? initialContent,
    }))

    useEffect(() => {
      if (!containerRef.current) return

      let destroyed = false

      const setup = async () => {
        const extensions = [
          lineNumbers(),
          highlightActiveLineGutter(),
          highlightActiveLine(),
          drawSelection(),
          history(),
          foldGutter(),
          indentOnInput(),
          bracketMatching(),
          closeBrackets(),
          autocompletion(),
          highlightSelectionMatches(),
          syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
          keymap.of([
            ...closeBracketsKeymap,
            ...defaultKeymap,
            ...searchKeymap,
            ...historyKeymap,
            indentWithTab,
          ]),
          EditorView.theme({
            '&': { height: '100%' },
            '.cm-scroller': { overflow: 'auto' },
            '.cm-content': {
              fontFamily:
                'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
              fontSize: '13px',
            },
            '.cm-gutters': { fontSize: '13px' },
          }),
        ]

        if (isDark) {
          extensions.push(oneDark)
        }

        const lang = detectLanguage(filename)
        if (lang && languageLoaders[lang]) {
          try {
            const langSupport = await languageLoaders[lang]()
            if (!destroyed) extensions.push(langSupport)
          } catch {
            /* fallback to no language support */
          }
        }

        if (destroyed) return

        extensions.push(
          phrasesCompartment.current.of(
            EditorState.phrases.of(phrasesRef.current),
          ),
          attributesCompartment.current.of(
            EditorView.contentAttributes.of(
              attributesRef.current
                ? { 'aria-label': attributesRef.current }
                : {},
            ),
          ),
          readOnlyCompartment.current.of(EditorState.readOnly.of(readOnly)),
        )

        const state = EditorState.create({
          doc: initialContent,
          extensions,
        })

        const view = new EditorView({
          state,
          parent: containerRef.current!,
        })

        viewRef.current = view
      }

      void setup()

      return () => {
        destroyed = true
        viewRef.current?.destroy()
        viewRef.current = null
      }
    }, [filename, isDark, initialContent, readOnly])

    useEffect(() => {
      const view = viewRef.current
      if (!view) return
      const input = getDialog(
        view,
        'cm-dialog',
      )?.dom.querySelector<HTMLInputElement>('input[name="line"]')
      const draft = input
        ? {
            value: input.value,
            start: input.selectionStart,
            end: input.selectionEnd,
            direction: input.selectionDirection,
          }
        : undefined
      const activeElement = view.dom.ownerDocument.activeElement
      view.dispatch({
        effects: [
          attributesCompartment.current.reconfigure(
            EditorView.contentAttributes.of(
              ariaLabel ? { 'aria-label': ariaLabel } : {},
            ),
          ),
          phrasesCompartment.current.reconfigure(
            EditorState.phrases.of(phrases),
          ),
        ],
      })
      if (!draft) return
      const panel = getDialog(view, 'cm-dialog')?.dom
      const nextInput =
        panel?.querySelector<HTMLInputElement>('input[name="line"]')
      if (!nextInput) return
      nextInput.value = draft.value
      nextInput.setSelectionRange(
        draft.start,
        draft.end,
        draft.direction ?? undefined,
      )
      const label = nextInput.closest('label')?.firstChild
      if (label?.nodeType === Node.TEXT_NODE)
        label.textContent = `${view.state.phrase('Go to line')}: `
      const submit = panel?.querySelector<HTMLButtonElement>(
        'button[type="submit"]',
      )
      if (submit) submit.textContent = view.state.phrase('go')
      if (activeElement === input) nextInput.focus()
      else if (
        activeElement instanceof HTMLElement &&
        activeElement.isConnected
      )
        activeElement.focus()
    }, [ariaLabel, phrases])

    return (
      <div
        ref={containerRef}
        className="h-full min-h-0 overflow-hidden rounded-md border"
      />
    )
  },
)
