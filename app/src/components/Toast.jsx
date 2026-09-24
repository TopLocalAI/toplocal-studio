import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle } from "@phosphor-icons/react";

export function useToast() {
  const [message, setMessage] = useState("");
  const timer = useRef(null);
  const show = useCallback((text) => {
    if (!text) return;
    clearTimeout(timer.current);
    setMessage(text);
    timer.current = setTimeout(() => setMessage(""), 3500);
  }, []);
  useEffect(() => () => clearTimeout(timer.current), []);
  return { message, show };
}

export function Toast({ message }) {
  if (!message) return null;
  return (
    <div className="toast" role="status">
      <CheckCircle size={19} weight="fill" />
      <span>{message}</span>
    </div>
  );
}
