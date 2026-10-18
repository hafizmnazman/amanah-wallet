import { Paperclip, RotateCcw, Send, X } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { api, type Clarification, type DocumentResponse, type PayoutResult, type PlanCard } from "@/api";
import { ErrorNote } from "@/components/common";
import { PayoutResults } from "@/components/plan/PayoutResults";
import { PlanCardView } from "@/components/plan/PlanCardView";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/fields";
import { cn } from "@/lib/utils";
import { useFund } from "@/session/FundContext";
import { useIdentity } from "@/session/IdentityContext";

import { ReaderFieldsCard } from "./ReaderFieldsCard";

interface Entry {
  id: number;
  from: "officer" | "agent";
  text: string;
  clarification?: Clarification;
  card?: PlanCard;
  results?: PayoutResult[];
  document?: { name: string; response: DocumentResponse };
  error?: unknown;
}

/** The finance officer's chat with the planner (task D1). */
export function ChatPanel() {
  const { identity } = useIdentity();
  const { programme } = useFund();
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [entries, setEntries] = useState<Entry[]>([]);
  const [activeCard, setActiveCard] = useState<PlanCard | null>(null);
  const [attached, setAttached] = useState<{ id: string; name: string }[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const nextId = useRef(1);
  const fileInput = useRef<HTMLInputElement>(null);
  const logEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEnd.current?.scrollIntoView?.({ block: "end" });
  }, [entries]);

  const push = (entry: Omit<Entry, "id">) => setEntries((list) => [...list, { ...entry, id: nextId.current++ }]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    push({ from: "officer", text: message });
    setDraft("");
    setBusy(true);
    try {
      if (activeCard) {
        const r = await api.correct(identity, { session_id: sessionId, batch_id: activeCard.batch_id, instruction: message });
        push({ from: "agent", text: r.reply, card: r.plan_card });
        setActiveCard(r.plan_card);
      } else {
        const r = await api.chat(identity, {
          session_id: sessionId,
          message,
          document_ids: attached.length ? attached.map((d) => d.id) : undefined,
          programme_code: programme.code,
        });
        setAttached([]);
        push({ from: "agent", text: r.reply, card: r.plan_card, clarification: r.clarification });
        if (r.plan_card) setActiveCard(r.plan_card);
      }
    } catch (error) {
      push({ from: "agent", text: "The request failed.", error });
    } finally {
      setBusy(false);
    }
  }

  async function confirm(card: PlanCard) {
    setBusy(true);
    try {
      const r = await api.confirm(identity, { session_id: sessionId, batch_id: card.batch_id });
      setActiveCard(null);
      push({ from: "agent", text: `Submitted ${r.results.length} payouts.`, results: r.results });
    } catch (error) {
      push({ from: "agent", text: "Confirming the batch failed.", error });
    } finally {
      setBusy(false);
    }
  }

  async function upload(file: File) {
    setBusy(true);
    try {
      const response = await api.uploadDocument(identity, file);
      setAttached((list) => [...list, { id: response.document_id, name: file.name }]);
      push({ from: "agent", text: `Read ${file.name}. It goes with your next message.`, document: { name: file.name, response } });
    } catch (error) {
      push({ from: "agent", text: `Reading ${file.name} failed.`, error });
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function startOver() {
    setSessionId(crypto.randomUUID());
    setEntries([]);
    setActiveCard(null);
    setAttached([]);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send(draft);
    }
  }

  const lastId = entries.length ? entries[entries.length - 1].id : 0;

  return (
    <section className="flex min-h-[70vh] flex-col gap-4" aria-label="Chat with the planner">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold">Payout planner</h1>
          <p className="text-sm text-muted">
            Working in {programme.fund}: {programme.name}. Amounts always come from the books.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={startOver} disabled={busy}>
          <RotateCcw className="h-4 w-4" aria-hidden />
          Start over
        </Button>
      </div>

      <div role="log" aria-live="polite" className="flex flex-1 flex-col gap-3" data-testid="chat-log">
        {entries.length === 0 && (
          <p className="rounded-md border border-dashed border-border p-4 text-sm text-muted">
            Ask for a payout batch, for example: Pay October&apos;s monthly aid for the Ipoh fakir programme.
          </p>
        )}
        {entries.map((entry) => (
          <div key={entry.id} className={cn("flex flex-col gap-2", entry.from === "officer" ? "items-end" : "items-stretch")}>
            <p
              data-testid={entry.from === "officer" ? "officer-message" : "agent-message"}
              className={cn(
                "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                entry.from === "officer" ? "bg-primary/15 text-foreground" : "self-start bg-surface-2",
              )}
            >
              {entry.text}
            </p>
            {entry.error !== undefined && <ErrorNote error={entry.error} />}
            {entry.clarification && (
              <div className="flex flex-col gap-2" data-testid="clarification">
                <p className="text-sm">{entry.clarification.question}</p>
                <div className="flex flex-wrap gap-2">
                  {entry.clarification.options.map((option) => (
                    <Button
                      key={option}
                      variant="secondary"
                      size="sm"
                      disabled={busy || entry.id !== lastId}
                      onClick={() => void send(option)}
                    >
                      {option}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            {entry.document && <ReaderFieldsCard name={entry.document.name} response={entry.document.response} />}
            {entry.card && (
              <PlanCardView
                card={entry.card}
                active={activeCard !== null && entry.card === activeCard}
                busy={busy}
                onConfirm={() => activeCard && void confirm(activeCard)}
              />
            )}
            {entry.results && <PayoutResults results={entry.results} />}
          </div>
        ))}
        <div ref={logEnd} />
      </div>

      <form onSubmit={onSubmit} className="sticky bottom-0 flex flex-col gap-2 border-t border-border bg-background pt-3">
        {attached.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {attached.map((doc) => (
              <span key={doc.id} className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-xs">
                <Paperclip className="h-3 w-3" aria-hidden />
                {doc.name}
                <button
                  type="button"
                  aria-label={`Remove ${doc.name}`}
                  onClick={() => setAttached((list) => list.filter((d) => d.id !== doc.id))}
                >
                  <X className="h-3 w-3" aria-hidden />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2">
          <input
            ref={fileInput}
            type="file"
            className="hidden"
            data-testid="document-input"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void upload(file);
            }}
          />
          <Button
            type="button"
            variant="outline"
            size="default"
            aria-label="Attach a document"
            onClick={() => fileInput.current?.click()}
            disabled={busy}
          >
            <Paperclip className="h-4 w-4" aria-hidden />
          </Button>
          <Textarea
            aria-label="Message"
            rows={1}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={activeCard ? "Ask for a change to this plan, or confirm it" : "Ask for a payout batch"}
            disabled={busy}
          />
          <Button type="submit" disabled={busy || !draft.trim()} aria-label="Send">
            <Send className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </form>
    </section>
  );
}
