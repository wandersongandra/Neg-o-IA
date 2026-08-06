export default function TypingIndicator() {
  return (
    <span
      className="inline-flex items-center gap-1.5 py-1"
      aria-label="NEGÃO está escrevendo"
      role="status"
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="size-1.5 animate-bounce rounded-full bg-[#00D4FF]"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  );
}
