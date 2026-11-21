import { t } from '../i18n';
import { useEffect, useId, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

/** Native modal keeps keyboard focus inside and restores it to its opener. */
export function Dialog({ title, onClose, children, className = '' }: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}) {
  const element = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = element.current;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog?.showModal();
    return () => {
      dialog?.close();
      // React can detach the dialog before its passive cleanup. Restore the
      // opener explicitly after that commit, including Escape and close button.
      queueMicrotask(() => { if (opener?.isConnected) opener.focus({ preventScroll: true }); });
    };
  }, []);
  return <dialog ref={element} className={`sheet-dialog ${className}`} aria-labelledby={titleId} onCancel={(event) => {
    event.preventDefault();
    onClose();
  }}>
    <header className="sheet-heading">
      <h2 id={titleId}>{title}</h2>
      <button className="icon-button" aria-label={t("Đóng cửa sổ")} onClick={onClose}><X size={21} aria-hidden="true" /></button>
    </header>
    <div className="sheet-content">{children}</div>
  </dialog>;
}
