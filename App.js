// App.js
// StartPage 역할을 담당하는 파일.
// SelectionModal에서 지역·극장·선호좌석을 수집한 뒤 MainPage로 라우팅한다.
// 영화 선택 / 인원 선택 / 결과 표시는 MainPage.jsx가 담당한다.

import React, { useState }                           from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import "./App.css";
import SeatSelector from "./SeatSelector";
import MainPage     from "./MainPage";

// ─────────────────────────────────────────────────────────────────────────────
//  SelectionModal  –  1단계: 지역 / 극장명 / 선호 좌석 수집
// ─────────────────────────────────────────────────────────────────────────────
const SelectionModal = ({ isOpen, onClose, onComplete }) => {
  const [region,   setRegion]   = useState("서울");
  const [theaters, setTheaters] = useState({
    cgv:         "강남",
    lottecinema: "건대입구",
    megabox:     "강남",
  });
  const [preferredSeat, setPreferredSeat] = useState({
    x_start: 0.0, x_end: 1.0, y_start: 0.0, y_end: 1.0,
  });

  if (!isOpen) return null;

  const handleTheaterChange = (cinema, value) =>
    setTheaters(prev => ({ ...prev, [cinema]: value }));

  const handleComplete = () => {
    if (!theaters.cgv && !theaters.lottecinema && !theaters.megabox) {
      alert("최소 한 곳 이상의 극장명을 입력해주세요.");
      return;
    }
    onComplete({ region, theaters, preferred_seat: preferredSeat });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      {/* ── 왼쪽 창: 지역 + 극장명 ── */}
      <div className="modal-window" onClick={e => e.stopPropagation()}>
        <h3 className="modal-header">사용자 조건 설정</h3>

        <div style={{ marginBottom: "20px" }}>
          <h4>1. 지역</h4>
          <input
            type="text" value={region}
            onChange={e => setRegion(e.target.value)}
            className="input-field"
          />
        </div>

        <div style={{ marginBottom: "20px", flex: 1 }}>
          <h4>2. 영화사별 극장명</h4>
          <p style={{ fontSize: "12px", color: "#666", marginTop: 0 }}>
            * 존재하지 않는 지점을 입력하면 크롤러에서 에러가 발생해요
          </p>
          <div className="theater-inputs">
            {[
              { key: "cgv",         label: "CGV" },
              { key: "lottecinema", label: "롯데시네마" },
              { key: "megabox",     label: "메가박스" },
            ].map(({ key, label }) => (
              <label key={key} className="input-label">
                {label}:
                <input
                  type="text" value={theaters[key]}
                  onChange={e => handleTheaterChange(key, e.target.value)}
                  className="input-field" style={{ marginTop: "5px" }}
                />
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* ── 오른쪽 창: 선호 좌석 선택 ── */}
      <div className="modal-window" onClick={e => e.stopPropagation()}>
        <h3 className="modal-header">선호 좌석 선택 영역</h3>

        <div style={{ marginBottom: "20px", flex: 1 }}>
          <h4>3. 선호 좌석 영역 선택</h4>
          <p style={{ fontSize: "12px", color: "#666", marginTop: 0 }}>
            * 원하는 구역 셀을 클릭하세요. 선택 해제 시 전체 구역으로 설정됩니다.
          </p>
          <SeatSelector
            onChange={val =>
              setPreferredSeat(
                val ?? { x_start: 0.0, x_end: 1.0, y_start: 0.0, y_end: 1.0 }
              )
            }
          />
        </div>

        <button onClick={handleComplete} className="btn-submit">
          저장 및 다음으로
        </button>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
//  StartPage  –  최초 진입 화면 (모달 열기 → MainPage로 이동)
// ─────────────────────────────────────────────────────────────────────────────
const StartPage = () => {
  const navigate      = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);

  // 모달 완료 → 수집 데이터를 state로 실어 MainPage로 이동
  const handleModalComplete = ({ region, theaters, preferred_seat }) => {
    setIsModalOpen(false);
    navigate("/main", {
      state: { region, theaters, preferred_seat },
    });
  };

  return (
    <div className="app-container">
      <div className="main-card">
        <h1 className="title">한 눈에 보는 영화 예매에 대한 모든 것</h1>
        <hr className="divider" />

        <div className="home-section">
          <p className="intro-text">블라블라블라 소개문구 블라블바블라</p>
          <button onClick={() => setIsModalOpen(true)} className="btn-primary">
            예매 조건 설정하기
          </button>
        </div>

        <SelectionModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onComplete={handleModalComplete}
        />
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
//  App  –  라우터 루트
// ─────────────────────────────────────────────────────────────────────────────
const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/"     element={<StartPage />} />
      <Route path="/main" element={<MainPage  />} />
    </Routes>
  </BrowserRouter>
);

export default App;