"use client";

import { Fragment, useMemo, type ReactNode } from "react";

const INLINE_RE =
  /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;

interface InlineProps {
  text: string;
}

function Inline({ text }: InlineProps) {
  const parts = useMemo(() => text.split(INLINE_RE), [text]);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
          return <em key={i}>{part.slice(1, -1)}</em>;
        }
        if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
          return (
            <code
              key={i}
              className="rounded bg-white/[0.06] px-1 py-0.5 font-mono-data text-[0.85em] text-[#7DD3FC]"
            >
              {part.slice(1, -1)}
            </code>
          );
        }
        const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
        if (link) {
          const href = link[2];
          const safe =
            /^(https?:|mailto:)/i.test(href) ||
            (typeof window !== "undefined" &&
              (() => {
                try {
                  const u = new URL(href, window.location.href);
                  return u.protocol === "http:" || u.protocol === "https:";
                } catch {
                  return false;
                }
              })());
          if (safe) {
            return (
              <a
                key={i}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#00D4FF] underline decoration-[#00D4FF]/40 underline-offset-2 hover:text-[#67E8F9]"
              >
                {link[1]}
              </a>
            );
          }
          return <Fragment key={i}>{link[1]}</Fragment>;
        }
        return <Fragment key={i}>{part}</Fragment>;
      })}
    </>
  );
}

function CodeBlock({ code }: { code: string }) {
  return (
    <div className="my-2 overflow-x-auto rounded-xl border border-white/[0.08] bg-black/40 p-3">
      <pre className="font-mono-data text-[12.5px] leading-relaxed text-[#E2E8F0]">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function ListBlock({ items, ordered }: { items: string[]; ordered: boolean }) {
  return (
    <ul className={`my-1.5 space-y-1 ${ordered ? "list-decimal" : "list-disc"} pl-5`}>
      {items.map((item, i) => (
        <li key={i} className="text-sm leading-relaxed text-[#E2E8F0]">
          <Inline text={item} />
        </li>
      ))}
    </ul>
  );
}

function parseBlocks(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const lines = text.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    const fenceMatch = line.match(/^```(\w*)\s*$/);
    if (fenceMatch) {
      const lang = fenceMatch[1];
      const buf: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith("```")) {
        buf.push(lines[i]);
        i += 1;
      }
      i += 1;
      nodes.push(
        <div key={`code-${nodes.length}`} className="group/code relative">
          {lang && (
            <span className="mb-1 inline-block font-mono-data text-[9px] uppercase tracking-widest text-[#64748B]">
              {lang}
            </span>
          )}
          <CodeBlock code={buf.join("\n")} />
        </div>
      );
      continue;
    }

    const headingMatch = line.match(/^(#{1,3})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const content = <Inline text={headingMatch[2]} />;
      nodes.push(
        level === 1 ? (
          <h3
            key={`h-${nodes.length}`}
            className="mt-3 mb-1 text-base font-semibold text-[#F8FAFC]"
          >
            {content}
          </h3>
        ) : level === 2 ? (
          <h4
            key={`h-${nodes.length}`}
            className="mt-2.5 mb-1 text-sm font-semibold text-[#F8FAFC]"
          >
            {content}
          </h4>
        ) : (
          <h5
            key={`h-${nodes.length}`}
            className="mt-2 mb-1 text-[13px] font-semibold text-[#F8FAFC]"
          >
            {content}
          </h5>
        )
      );
      i += 1;
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i += 1;
      }
      nodes.push(<ListBlock key={`ul-${nodes.length}`} items={items} ordered={false} />);
      continue;
    }

    if (/^\s*\d{1,2}[.)]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d{1,2}[.)]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d{1,2}[.)]\s+/, ""));
        i += 1;
      }
      nodes.push(<ListBlock key={`ol-${nodes.length}`} items={items} ordered={true} />);
      continue;
    }

    if (line.trim() === "") {
      i += 1;
      continue;
    }

    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].match(/^(#{1,3}\s|```|[-*]\s|\d{1,2}[.)]\s)/)
    ) {
      para.push(lines[i]);
      i += 1;
    }
    nodes.push(
      <p key={`p-${nodes.length}`} className="my-1 text-sm leading-relaxed text-[#E2E8F0]">
        <Inline text={para.join(" ")} />
      </p>
    );
  }

  return nodes;
}

export default function Markdown({ text }: { text: string }) {
  const nodes = useMemo(() => parseBlocks(text), [text]);
  return <div className="space-y-0.5">{nodes}</div>;
}
