import { motion } from "framer-motion";

/**
 * ChatBubble — bulle de chat (utilisateur ou assistant).
 *
 * Props:
 *   role: "user" | "assistant"
 *   text: contenu
 *   streaming: bool — affiche le curseur clignotant
 */
export const ChatBubble = ({ role = "assistant", text = "", streaming = false }) => {
  const isUser = role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} bubble-in`}
      data-testid={isUser ? "user-bubble" : "assistant-bubble"}
    >
      <div className={`max-w-[85%] sm:max-w-[78%] rounded-2xl px-4 py-3 ${
        isUser
          ? "bg-gradient-to-br from-[#1E3A6E] to-[#2A5BAF]/85 border border-[#3B6FCC]/30 shadow-[0_6px_24px_rgba(45,111,224,0.18)]"
          : "bg-white/[0.025] border border-white/[0.06]"
      }`}>
        <div
          className={`font-mono text-[10px] uppercase tracking-[0.22em] mb-1.5 ${
            isUser ? "text-[#9FC4FF]" : "text-[#6BA8FF]"
          }`}
          data-testid={isUser ? "user-bubble-label" : "assistant-bubble-label"}
        >
          {isUser ? "Toi" : "Laurent.ia"}
        </div>
        <div className="font-sans text-[15px] sm:text-base leading-relaxed text-[#F1F4FA] whitespace-pre-wrap break-words">
          {text}
          {streaming && (
            <span className="inline-block w-[7px] h-[16px] align-[-2px] ml-1 bg-[#6BA8FF]/85 animate-pulse rounded-[1px]" />
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default ChatBubble;
