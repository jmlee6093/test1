import React, { useState }                           from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import "./App.css";
import SeatSelector from "./SeatSelector";
import MainPage     from "./MainPage";

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
      <div className="modal-window" onClick={(e) => e.stopPropagation()}>
        <h3 className="modal-header">사용자 조건 설정</h3>
        
        <div style={{ marginBottom: '20px' }}>
          <h4>1. 지역</h4>
          <input 
            type="text" value={region} onChange={(e) => setRegion(e.target.value)} 
            className="input-field"
          />
        </div>

        <div style={{ marginBottom: '20px', flex: 1 }}>
          <h4>2. 영화사별 극장명</h4>
          <p style={{ fontSize: '12px', color: '#666', marginTop: 0 }}>* 존재하지 않는 지점을 입력하면 크롤러에서 에러 발생했어요</p>
          <div className="theater-inputs">
            <label className="input-label">
              CGV: 
              <input type="text" value={theaters.cgv} onChange={(e) => handleTheaterChange('cgv', e.target.value)} className="input-field" style={{ marginTop: '5px' }} />
            </label>
            <label className="input-label">
              롯데시네마: 
              <input type="text" value={theaters.lottecinema} onChange={(e) => handleTheaterChange('lottecinema', e.target.value)} className="input-field" style={{ marginTop: '5px' }} />
            </label>
            <label className="input-label">
              메가박스: 
              <input type="text" value={theaters.megabox} onChange={(e) => handleTheaterChange('megabox', e.target.value)} className="input-field" style={{ marginTop: '5px' }} />
            </label>
          </div>
        </div>
      </div>

      <div className="modal-window" onClick={e => e.stopPropagation()}>
        <h3 className="modal-header">선호 좌석 선택 영역</h3>

        <div style={{ marginBottom: "20px", flex: 1 }}>
          <h4>3. 상대 좌표 (0.0 ~ 1.0)</h4>
          <p style={{ fontSize: "12px", color: "#666", marginTop: 0 }}>
            * 원하는 구역 셀을 클릭하세요.
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

const StartPage = () => {
  const navigate      = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
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

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/"     element={<StartPage />} />
      <Route path="/main" element={<MainPage  />} />
    </Routes>
  </BrowserRouter>
);

export default App;