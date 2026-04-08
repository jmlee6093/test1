// MainPage.jsx
// 2단계: 영화 선택 + 인원 설정 → Flask API POST → 결과 표시
//
// useLocation().state 로 받는 데이터 (App.js StartPage → navigate("/main", { state }))
//   state.region        : string  – 지역명  (예: "서울")
//   state.theaters      : object  – { cgv, lottecinema, megabox }  각 극장 지점명
//   state.preferred_seat: object  – { x_start, x_end, y_start, y_end }

import { useState }                   from "react";
import { useNavigate, useLocation }   from "react-router-dom";

const MOVIES = [
  { movie_index: 0, rank: 1, title: "왕과 사는 남자",               rating: "9.18", audience: "16,129,508", release_date: "2026-02-04" },
  { movie_index: 1, rank: 2, title: "프로젝트 헤일메리",            rating: "8.78", audience: "1,670,264",  release_date: "2026-03-18" },
  { movie_index: 2, rank: 3, title: "끝장수사",                     rating: "6.41", audience: "63,479",     release_date: "2026-04-02" },
  { movie_index: 3, rank: 4, title: "네가 마지막으로 남긴 노래",    rating: "8.79", audience: "57,799",     release_date: "2026-04-01" },
  { movie_index: 4, rank: 5, title: "극장판 귀멸의 칼날: 무한성편", rating: "7.51", audience: "5,784,883",  release_date: "2025-08-22" },
  { movie_index: 5, rank: 6, title: "명탐정 코난: 세기말의 마술사", rating: "9.14", audience: "82,030",     release_date: "2026-03-27" },
];

// ─── 스타일 ───────────────────────────────────────────────────────────────────
const styles = {
  page: {
    background: "#ffffff",
    minHeight: "100vh",
    padding: "24px 32px",
    fontFamily: "sans-serif",
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
  },
  heading: {
    color: "#111827",
    fontSize: "20px",
    marginBottom: "4px",
    flexShrink: 0,
  },
  subHeading: {
    color: "#6b7280",
    fontSize: "13px",
    marginBottom: "16px",
  },
  cardList: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  card: {
    display: "flex",
    alignItems: "center",
    gap: "20px",
    background: "#f9fafb",
    border: "1px solid #e5e7eb",
    borderRadius: "12px",
    padding: "14px 20px",
    cursor: "pointer",
    transition: "background 0.15s, border-color 0.15s, transform 0.15s",
  },
  cardHovered: {
    background: "#eff6ff",
    borderColor: "#4a90d9",
    transform: "translateX(4px)",
  },
  rank:            { fontSize: "22px", fontWeight: "700", color: "#4a90d9", width: "36px", textAlign: "center", flexShrink: 0 },
  title:           { fontSize: "15px", fontWeight: "600", color: "#111827", flex: 1, wordBreak: "keep-all" },
  dataGroup:       { display: "flex", gap: "24px" },
  dataItem:        { display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "2px" },
  dataLabel:       { fontSize: "11px", color: "#9ca3af" },
  dataValue:       { fontSize: "13px", color: "#374151", fontWeight: "500" },
  dataValueRating: { fontSize: "13px", color: "#f59e0b", fontWeight: "600" },
  statusText:      { fontSize: "14px", color: "#6b7280", textAlign: "center", marginTop: "8px" },

  // 인원 선택 패널
  peoplePanel: {
    display: "flex",
    alignItems: "center",
    gap: "24px",
    background: "#f0f4ff",
    border: "1px solid #c7d7f4",
    borderRadius: "12px",
    padding: "14px 20px",
    marginBottom: "20px",
    flexShrink: 0,
  },
  peopleLabel:    { fontSize: "14px", fontWeight: "600", color: "#374151" },
  counterWrap:    { display: "flex", alignItems: "center", gap: "10px" },
  counterBtn: {
    width: "28px", height: "28px",
    borderRadius: "50%",
    border: "1px solid #4a90d9",
    background: "#ffffff",
    color: "#4a90d9",
    fontSize: "18px",
    cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center",
    lineHeight: 1,
  },
  counterValue:   { fontSize: "16px", fontWeight: "700", color: "#111827", minWidth: "20px", textAlign: "center" },

  // 결과 패널
  resultSection: {
    marginTop: "30px",
  },
  resultHeading: {
    fontSize: "18px",
    fontWeight: "700",
    color: "#111827",
    marginBottom: "12px",
  },
  cinemaCard: {
    border: "1px solid #e5e7eb",
    borderRadius: "10px",
    padding: "16px",
    marginBottom: "16px",
    background: "#ffffff",
  },
  cinemaTitle: {
    fontSize: "16px",
    fontWeight: "700",
    textTransform: "uppercase",
    color: "#1f2937",
    marginBottom: "10px",
    paddingBottom: "8px",
    borderBottom: "2px solid #f3f4f6",
  },
  showtimeItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px",
    border: "1px solid #f3f4f6",
    borderRadius: "8px",
    marginBottom: "8px",
  },
  ticketingBtn: {
    padding: "8px 16px",
    background: "#E50914",
    color: "#ffffff",
    textDecoration: "none",
    borderRadius: "6px",
    fontWeight: "700",
    fontSize: "13px",
  },
};

// ─── 영화 카드 ────────────────────────────────────────────────────────────────
function MovieCard({ movie, onClick, disabled }) {
  const [hovered, setHovered] = useState(false);

  const cardStyle = {
    ...styles.card,
    ...(hovered && !disabled ? styles.cardHovered : {}),
    opacity: disabled ? 0.5 : 1,
    cursor:  disabled ? "not-allowed" : "pointer",
  };

  return (
    <article
      style={cardStyle}
      onClick={() => !disabled && onClick(movie)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={styles.rank}>{movie.rank}</div>
      <h3 style={styles.title}>{movie.title}</h3>
      <div style={styles.dataGroup}>
        <div style={styles.dataItem}>
          <span style={styles.dataLabel}>평점</span>
          <span style={styles.dataValueRating}>{movie.rating}</span>
        </div>
        <div style={styles.dataItem}>
          <span style={styles.dataLabel}>누적 관객</span>
          <span style={styles.dataValue}>{movie.audience}명</span>
        </div>
        <div style={styles.dataItem}>
          <span style={styles.dataLabel}>개봉일</span>
          <span style={styles.dataValue}>{movie.release_date}</span>
        </div>
      </div>
    </article>
  );
}

// ─── 인원 카운터 ──────────────────────────────────────────────────────────────
function Counter({ label, value, onChange, disabled }) {
  return (
    <div style={styles.counterWrap}>
      <span style={styles.peopleLabel}>{label}</span>
      <button style={styles.counterBtn} onClick={() => onChange(Math.max(0, value - 1))} disabled={disabled}>−</button>
      <span style={styles.counterValue}>{value}</span>
      <button style={styles.counterBtn} onClick={() => onChange(Math.min(8, value + 1))} disabled={disabled}>+</button>
    </div>
  );
}

// ─── 결과 표시 ────────────────────────────────────────────────────────────────
function ResultSection({ results, onReset }) {
  const getTicketingUrl = (cinema) => {
    switch (cinema.toLowerCase()) {
      case "cgv":         return "https://cgv.co.kr/cnm/movieBook/movie";
      case "lottecinema": return "https://www.lottecinema.co.kr/NLCHS/Ticketing";
      case "megabox":     return "https://www.megabox.co.kr/booking";
      default:            return "#";
    }
  };

  return (
    <div style={styles.resultSection}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <span style={styles.resultHeading}>검색 결과</span>
        <button onClick={onReset} className="btn-reset">다시 선택하기</button>
      </div>

      {Object.entries(results).map(([cinema, data]) => (
        <div key={cinema} style={styles.cinemaCard}>
          <div style={styles.cinemaTitle}>
            {cinema.toUpperCase()} — {data.theater} 극장
          </div>

          {data.status === "error" ? (
            <pre className="error-msg">{data.message}</pre>
          ) : !data.showtimes || data.showtimes.length === 0 ? (
            <p style={{ color: "#9ca3af", fontSize: "14px" }}>조건에 맞는 좌석이 없습니다.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {data.showtimes.map((show, idx) => (
                <li key={idx} style={styles.showtimeItem}>
                  <div>
                    <strong style={{ fontSize: "18px", display: "block", marginBottom: "4px" }}>
                      {show.showtime}
                    </strong>
                    <span style={{ color: "#555", fontSize: "13px" }}>
                      조건 만족 좌석 수: <strong>{show.total}개</strong><br />
                      좌석 번호: {show.seats.length > 0 ? show.seats.join(", ") : "없음"}
                    </span>
                  </div>
                  <a href={getTicketingUrl(cinema)} target="_blank" rel="noreferrer" style={styles.ticketingBtn}>
                    예매 이동
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  MainPage  –  메인 컴포넌트
// ─────────────────────────────────────────────────────────────────────────────
export default function MainPage() {
  const navigate       = useNavigate();
  const { state }      = useLocation();

  // 인원 수 (성인 / 청소년)
  const [adultCount,  setAdultCount]  = useState(2);
  const [youthCount,  setYouthCount]  = useState(0);

  // 서버 통신 상태
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState(null);
  const [crawlResults, setCrawlResults] = useState(null);

  // 잘못된 진입 처리
  if (!state) {
    return (
      <div style={{ padding: "40px", fontFamily: "sans-serif" }}>
        <p>잘못된 접근입니다. 처음부터 다시 시작해주세요.</p>
        <button onClick={() => navigate("/")}>처음으로</button>
      </div>
    );
  }

  async function handleMovieClick(movie) {
    setLoading(true);
    setError(null);
    setCrawlResults(null);

    // App.js SelectionModal에서 전달받은 state + 현재 페이지에서 선택한 데이터를 하나의 body로 취합
    const payload = {
      movie_name:     movie.title,
      region:         state.region,
      theaters:       state.theaters,          // { cgv, lottecinema, megabox }
      ticket_config:  {
        "성인":   adultCount,
        "청소년": youthCount,
      },
      preferred_seat: state.preferred_seat,
      num_workers:    3,
    };

    try {
      const response = await fetch("http://localhost:5000/api/search", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });

      if (!response.ok) throw new Error(`서버 오류: ${response.status}`);

      const data = await response.json();
      if (data.status === "success" || data.results) {
        setCrawlResults(data.results);
      } else {
        setError("서버 응답 형식 오류");
      }
    } catch (err) {
      setError(`요청 실패: ${err.message}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  const totalCount = adultCount + youthCount;

  return (
    <div style={styles.page}>
      {/* ── 헤더 ── */}
      <h2 style={styles.heading}>박스오피스 순위</h2>
      <p style={styles.subHeading}>
        {state.region} · {Object.values(state.theaters).filter(Boolean).join(" / ")}
      </p>

      {/* ── 인원 선택 패널 ── */}
      <div style={styles.peoplePanel}>
        <span style={{ ...styles.peopleLabel, marginRight: "8px" }}>인원 선택</span>
        <Counter label="성인"   value={adultCount} onChange={setAdultCount} disabled={loading} />
        <Counter label="청소년" value={youthCount} onChange={setYouthCount} disabled={loading} />
        {totalCount === 0 && (
          <span style={{ fontSize: "12px", color: "#ef4444", marginLeft: "8px" }}>
            * 1명 이상 선택해주세요
          </span>
        )}
      </div>

      {/* ── 상태 메시지 ── */}
      {error   && <p style={{ ...styles.statusText, color: "#ef4444" }}>{error}</p>}
      {loading && <p style={styles.statusText}>🔍 크롤링 중입니다... 잠시만 기다려 주세요.</p>}

      {/* ── 결과가 없을 때: 영화 목록 표시 ── */}
      {!crawlResults && (
        <div style={styles.cardList}>
          {MOVIES.map((movie) => (
            <MovieCard
              key={movie.movie_index}
              movie={movie}
              onClick={handleMovieClick}
              disabled={loading || totalCount === 0}
            />
          ))}
        </div>
      )}

      {/* ── 결과 표시 ── */}
      {crawlResults && (
        <ResultSection
          results={crawlResults}
          onReset={() => setCrawlResults(null)}
        />
      )}
    </div>
  );
}