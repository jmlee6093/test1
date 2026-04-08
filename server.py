# Flask 오케스트레이션 서버 (중앙 제어 서버)
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

from lottecinema_crawler import run_lottecinema
from megabox_crawler      import run_megabox
from cgv_crawler          import run_cgv

app = Flask(__name__)

CRAWLERS = {
    "lottecinema": run_lottecinema,
    "megabox":     run_megabox,
    "cgv":         run_cgv,
}

#  요청 파라미터 파싱 헬퍼
def _build_crawler_params(body: dict, cinema: str) -> dict:
   
    theaters = body.get("theaters", {})

    return {
        "movie_name":     body.get("movie_name", ""),
        "region":         body.get("region", "서울"),
        "theater":        theaters.get(cinema, ""),
        "ticket_config":  body.get("ticket_config", {"성인": 2}),
        "preferred_seat": body.get("preferred_seat",
                                   {"x_start": 0.0, "x_end": 1.0,
                                    "y_start": 0.0, "y_end": 1.0}),
        "num_workers":    body.get("num_workers", 3),
    }

@app.route("/api/search", methods=["POST"])
def search_seats():
    
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"status": "error", "message": "요청 body가 비어있거나 JSON 형식이 아닙니다."}), 400

    theaters = body.get("theaters", {})
    active_cinemas = [c for c in CRAWLERS if c in theaters and theaters[c]]

    if not active_cinemas:
        return jsonify({"status": "error",
                        "message": "theaters 필드에 유효한 영화사/지점 정보가 없습니다."}), 400

    combined_results: dict = {}

    #ThreadPoolExecutor로 활성 영화사 크롤러 동시 실행
    with ThreadPoolExecutor(max_workers=len(active_cinemas)) as executor:

        future_to_cinema = {
            executor.submit(
                CRAWLERS[cinema],
                _build_crawler_params(body, cinema)
            ): cinema
            for cinema in active_cinemas
        }

        for future in as_completed(future_to_cinema):
            cinema = future_to_cinema[future]
            try:
                result = future.result()
                combined_results[cinema] = result

            except Exception:
                # 개별 크롤러 오류는 전체 응답을 막지 않음
                combined_results[cinema] = {
                    "cinema":    cinema,
                    "theater":   theaters.get(cinema, ""),
                    "status":    "error",
                    "message":   traceback.format_exc(),
                    "showtimes": [],
                }

    return jsonify({
        "status":  "success",
        "results": combined_results,
    })


#  GET /api/health  ─ 서버 상태 확인
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "registered_crawlers": list(CRAWLERS.keys())})

#  실행 진입점
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)