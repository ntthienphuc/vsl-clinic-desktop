import { useEffect, useId, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

/** Native modal keeps keyboard focus inside and restores it to its opener. */
export function Dialog({ title, onClose, children }: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const element = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = element.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return <dialog ref={element} className="sheet-dialog" aria-labelledby={titleId} onCancel={(event) => {
    event.preventDefault();
    onClose();
  }}>
    <header className="sheet-heading">
      <h2 id={titleId}>{title}</h2>
      <button className="icon-button" aria-label="Đóng cửa sổ" onClick={onClose}><X size={21} /></button>
    </header>
    <div className="sheet-content">{children}</div>
  </dialog>;
}
