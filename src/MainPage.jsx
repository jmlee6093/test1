// MainPage.jsx
// 2단계: 영화 선택 + 인원 설정 → Flask API POST → 결과 표시
//
// useLocation().state 로 받는 데이터 (App.js StartPage → navigate("/main", { state }))
//   state.region        : string  – 지역명  (예: "서울")
//   state.theaters      : object  – { cgv, lottecinema, megabox }  각 극장 지점명
//   state.preferred_seat: object  – { x_start, x_end, y_start, y_end }

import { useState }                 from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "./MainPage.css";

const MOVIES = [
  { movie_index: 0, rank: 1, title: "왕과 사는 남자",               rating: "9.18", audience: "16,129,508", release_date: "2026-02-04", image: "/images/index1_movie_image.webp" },
  { movie_index: 1, rank: 2, title: "프로젝트 헤일메리",            rating: "8.78", audience: "1,670,264",  release_date: "2026-03-18", image: "/images/index2_movie_image.webp" },
  { movie_index: 2, rank: 3, title: "끝장수사",                     rating: "6.41", audience: "63,479",     release_date: "2026-04-02", image: "/images/index3_movie_image.webp" },
  { movie_index: 3, rank: 4, title: "네가 마지막으로 남긴 노래",    rating: "8.79", audience: "57,799",     release_date: "2026-04-01", image: "/images/index4_movie_image.webp" },
  { movie_index: 4, rank: 5, title: "극장판 귀멸의 칼날: 무한성편", rating: "7.51", audience: "5,784,883",  release_date: "2025-08-22", image: "/images/index5_movie_image.webp" },
  { movie_index: 5, rank: 6, title: "명탐정 코난: 세기말의 마술사", rating: "9.14", audience: "82,030",     release_date: "2026-03-27", image: "/images/index6_movie_image.webp" },
];

// ─── 영화 카드 ────────────────────────────────────────────────────────────────
function MovieCard({ movie, onClick, disabled }) {
  return (
    <article
      className={`mp-card${disabled ? " mp-card--disabled" : ""}`}
      onClick={() => !disabled && onClick(movie)}
      style={{ backgroundImage: `url(${movie.image})` }}
    >
      <div className="mp-card__rank">{movie.rank}</div>
      <h3 className="mp-card__title">{movie.title}</h3>
      <div className="mp-card__data-group">
        <div className="mp-card__data-item">
          <span className="mp-card__data-label">평점</span>
          <span className="mp-card__data-value--rating">{movie.rating}</span>
        </div>
        <div className="mp-card__data-item">
          <span className="mp-card__data-label">누적 관객</span>
          <span className="mp-card__data-value">{movie.audience}명</span>
        </div>
        <div className="mp-card__data-item">
          <span className="mp-card__data-label">개봉일</span>
          <span className="mp-card__data-value">{movie.release_date}</span>
        </div>
      </div>
    </article>
  );
}

function Counter({ label, value, onChange, disabled }) {
  return (
    <div className="mp-counter-wrap">
      <span className="mp-people-label">{label}</span>
      <button className="mp-counter-btn" onClick={() => onChange(Math.max(0, value - 1))} disabled={disabled}>−</button>
      <span className="mp-counter-value">{value}</span>
      <button className="mp-counter-btn" onClick={() => onChange(Math.min(8, value + 1))} disabled={disabled}>+</button>
    </div>
  );
}

function ResultSection({ results, onReset }) {
  const getTicketingUrl = (cinema) => {
    switch (cinema.toLowerCase()) {
      case "cgv":         return "https://cgv.co.kr/cnm/movieBook/movie";
      case "lottecinema": return "https://www.lottecinema.co.kr/NLCHS/Ticketing";
      case "megabox":     return "https://www.megabox.co.kr/booking";
      default:            return "#";
    }
  };

  const CINEMA_ORDER = ["cgv", "lottecinema", "megabox"];
  const CINEMA_LABEL = { cgv: "CGV", lottecinema: "롯데시네마", megabox: "메가박스" };

  return (
    <div className="mp-result-section">
      <div className="mp-result-header">
        <span className="mp-result-heading">검색 결과</span>
        <button onClick={onReset} className="btn-reset">다시 선택하기</button>
      </div>

      {CINEMA_ORDER.map((cinema) => {
        const data = results[cinema];
        const validShowtimes = data?.showtimes?.filter(s => s.total > 0) ?? [];

        return (
          <div key={cinema} className="mp-cinema-card">
            <div className="mp-cinema-title">
              {CINEMA_LABEL[cinema]} — {data?.theater ?? ""} 
            </div>

            {!data || data.status === "error" || validShowtimes.length === 0 ? (
              <p className="mp-no-seats">조건에 맞는 좌석이 없습니다.</p>
            ) : (
              <ul className="mp-showtime-list">
                {validShowtimes.map((show, idx) => (
                  <li key={idx} className="mp-showtime-item">
                    <div>
                      <strong className="mp-showtime-time">{show.showtime}</strong>
                      <span className="mp-showtime-info">
                        조건 만족 좌석 수: <strong>{show.total}개</strong><br />
                        좌석 번호: {show.seats.join(", ")}
                      </span>
                    </div>
                    <a href={getTicketingUrl(cinema)} target="_blank" rel="noreferrer" className="mp-ticketing-btn">
                      예매 이동
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function MainPage() {
  const navigate       = useNavigate();
  const { state }      = useLocation();

  const [adultCount,   setAdultCount]   = useState(2);
  const [youthCount,   setYouthCount]   = useState(0);

  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState(null);
  const [crawlResults, setCrawlResults] = useState(null);

  if (!state) {
    return (
      <div className="mp-error-page">
        <p>잘못된 접근입니다. 처음부터 다시 시작해주세요.</p>
        <button onClick={() => navigate("/")}>처음으로</button>
      </div>
    );
  }

  async function handleMovieClick(movie) {
    setLoading(true);
    setError(null);
    setCrawlResults(null);

    const payload = {
      movie_name:     movie.title,
      region:         state.region,
      theaters:       state.theaters,       
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
    <div className="mp-page">
      <p className="mp-sub-heading">
        {state.region} · {Object.values(state.theaters).filter(Boolean).join(" / ")}
      </p>

      <div className="mp-people-panel">
        <span className="mp-people-label--lead">인원 선택</span>
        <Counter label="성인"   value={adultCount} onChange={setAdultCount} disabled={loading} />
        <Counter label="청소년" value={youthCount} onChange={setYouthCount} disabled={loading} />
        {totalCount === 0 && (
          <span className="mp-people-warn">* 1명 이상 선택해주세요</span>
        )}
      </div>

      {error   && <p className="mp-status-text mp-status-text--error">{error}</p>}
      {loading && <p className="mp-status-text">크롤링 중입니다... 잠시만 기다려 주세요.</p>}

      {!crawlResults && (
        <div className="mp-card-list">
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

      {crawlResults && (
        <ResultSection
          results={crawlResults}
          onReset={() => setCrawlResults(null)}
        />
      )}
    </div>
  );
}