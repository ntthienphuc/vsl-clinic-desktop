import { t, useInterfaceLanguage } from './i18n';
import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AlertCircle, HeartPulse, X } from 'lucide-react';
import { useClinic } from './api';
import { AppHeader } from './components/Shared';
const DoctorView = React.lazy(() => import('./DoctorView').then(module => ({ default: module.DoctorView })));
const PatientView = React.lazy(() => import('./PatientView').then(module => ({ default: module.PatientView })));
import type { Role } from './types';
import { version as appVersion } from '../package.json';
import './styles.css';
import './clinic-ui.css';
import './workspace.css';

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: string }> {
  state = { error: '' };
  static getDerivedStateFromError(error: Error) {
    return { error: error.message };
  }
  render() {
    if (this.state.error) {
      return <main className="startup"><HeartPulse size={44} /><h1>{t("Chưa mở được giao diện")}</h1><p>{t(this.state.error)}</p>{location.pathname.startsWith('/patient') ? <p>{t('Nhờ bác sĩ mở lại màn hình.')}</p> : <button className="button primary" onClick={() => location.reload()}>{t("Mở lại màn hình")}</button>}</main>;
    }
    return this.props.children;
  }
}

function App() {
  const language = useInterfaceLanguage();
  const role: Role = location.pathname.startsWith('/patient') ? 'patient' : 'doctor';
  const { bootstrap, state, connected, error } = useClinic(role);
  const [notice, setNotice] = useState('');
  const [operations, setOperations] = useState(0);
  const run = useCallback(async (action: () => Promise<unknown>) => {
    setOperations((value) => value + 1);
    try {
      await action();
      setNotice('');
    } catch (problem) {
      setNotice((problem as Error).message);
    } finally {
      setOperations((value) => value - 1);
    }
  }, []);
  useEffect(() => {
    document.title = `VSL Clinic · ${t(role === 'doctor' ? 'Bác sĩ' : 'Người bệnh')}`;
    document.documentElement.lang = language;
  }, [role, language]);
  useEffect(() => {
    if (!notice) {
      return;
    }
    const timeout = setTimeout(() => setNotice(''), 10000);
    return () => clearTimeout(timeout);
  }, [notice]);
  if (!bootstrap || !state) {
    return <main className="startup"><span className="brand-mark large"><HeartPulse size={38} /></span><h1>VSL Clinic</h1><p>{t(error) || t("Đang chuẩn bị không gian giao tiếp…")}</p><span>{t("Hai màn hình. Một cuộc trò chuyện.")}</span></main>;
  }
  return <div className={`app ${role}`}>
    {role === 'doctor' && <a className="skip-link" href="#clinic-workspace">{t('Đến nội dung trao đổi')}</a>}
    <AppHeader role={role} connected={connected} state={state} run={run} />
    {!connected && <div className="connection-banner" role="status"><AlertCircle size={16} /> {t(" Đang kết nối lại. Vui lòng chờ trước khi tiếp tục trao đổi.")}</div>}
    <React.Suspense fallback={<main className="startup"><p>{t('Đang chuẩn bị không gian giao tiếp…')}</p></main>}>{role === 'doctor'
      ? <DoctorView bootstrap={bootstrap} state={state} connected={connected} run={run} busy={operations > 0} />
      : <PatientView bootstrap={bootstrap} state={state} connected={connected} />}</React.Suspense>
    <footer className="app-footer"><span>VSL Clinic</span><span>{t("Bản thử nghiệm · ")}{appVersion}</span></footer>
    {notice && <div className="toast" role="alert"><AlertCircle size={20} /><span>{t(notice)}</span><button className="icon-button" aria-label={t("Đóng thông báo")} onClick={() => setNotice('')}><X size={18} /></button></div>}
  </div>;
}

createRoot(document.getElementById('root')!).render(<ErrorBoundary><App /></ErrorBoundary>);
