#크롤링 테스트
# (01.12 수정사항) prefs 변수 만들어 위치 정보 권한 강제로 차단하는 코드 만들었습니다. 제 환경 문제 때문에 만든거니 종민님 테스트 환경에서는 필요할때 쓰면 될거예요.
# ㄴ 참고한 링크 - https://velog.io/@sangyeon217/mocking-geolocation
# v1.1.0 수정사항 - 주요 기능: 예매표 순회 기능, 멀티스레딩 추가
# v1.2.0 수정사항 - movie_index → movie_name 기반 매칭으로 변경
#   공백 제거 + 소문자 변환 후 in 연산자로 유연하게 매칭
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
import threading
import time
import re
import math

# ======================계정 정보====================
KAKAO_ID = "jmlee6093020621@gmail.com"
KAKAO_PW = "jongmin0329!"

#전역변수 삭제하고 생성자로 설정
class CGVActor:
    def __init__(self, actor_id, region, ticket_config, preferred_seat,
                 results_list, results_lock, error_event):
        self.actor_id       = actor_id
        self.region         = region
        self.ticket_config  = ticket_config
        self.preferred_seat = preferred_seat
        self.results_list   = results_list
        self.results_lock   = results_lock
        self.error_event    = error_event   # 영화 미발견 시 플래그

        options = Options()
        options.add_experimental_option("detach", True)
        prefs = {"profile.default_content_setting_values.geolocation": 2}
        options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=options)

        max_cols = 2
        x_pos = (actor_id % max_cols) * 960
        y_pos = (actor_id // max_cols) * 520
        self.driver.set_window_position(x_pos, y_pos)
        self.driver.set_window_size(960, 520)

        self.login()

    def login(self):
        print(f"[{self.actor_id}번] CGV 접속 및 카카오 로그인 진행")
        url = "https://accounts.kakao.com/login/?continue=https%3A%2F%2Fkauth.kakao.com%2Foauth%2Fauthorize%3Fclient_id%3D3d5fa93996f920c3ad88e8fe8198f2dc%26redirect_uri%3Dhttps%253A%252F%252Fcgv.co.kr%252Fapi%252Fauth%252Fcallback%252Fkakao%26response_type%3Dcode%26state%3D80cf9c11-a407-4eaa-9c9c-d69d5ee2420b%26through_account%3Dtrue%26auth_tran_id%3DtFOoLFQ17J64MMH2sBxBj7kkdfiqSz2bbJoj6nwhChcWnwAAAZuD9DDm#login"
        self.driver.get(url)
        try:
            id_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "loginId")))
            id_input.send_keys(KAKAO_ID)
            time.sleep(0.5)

            pw_input = self.driver.find_element(By.NAME, "password")
            pw_input.send_keys(KAKAO_PW)
            time.sleep(0.5)

            save_login = self.driver.find_element(
                By.XPATH, "//label[contains(.,'간편로그인 정보 저장')]")
            save_login.click()
            pw_input.send_keys(Keys.ENTER)
            time.sleep(4)
        except Exception as e:
            print(f"[{self.actor_id}번] 로그인 실패: {e}")

        try:
            popup_close = self.driver.find_element(
                By.XPATH, "//button[contains(text(),'오늘은 그만 보기')]")
            popup_close.click()
            time.sleep(2)
        except:
            pass

    # ── [수정] movie_index → movie_name 기반 매칭 ──────────────────────────
    def select_movie_and_theater(self, movie_name):
        self.driver.get("http://www.cgv.co.kr/")
        time.sleep(3)

        try:
            movie_btns = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "button[class*='mainMovieChartCard_linkBtn']"))
                )

            # 공백 제거 + 소문자 변환 후 in 연산자로 유연하게 매칭
            target_norm = movie_name.replace(" ", "").lower()
            target = None
            for btn in movie_btns:
                btn_norm = btn.text.replace(" ", "").lower()
                if target_norm in btn_norm or btn_norm in target_norm:
                    target = btn
                    break

            if target is None:
                print(f"[{self.actor_id}번] '{movie_name}'과 매칭되는 영화를 CGV 목록에서 찾지 못했습니다.")
                self.error_event.set()
                return False

            self.driver.execute_script("arguments[0].scrollIntoView(true);", target)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", target)
            time.sleep(3)

            reservation = self.driver.find_element(By.CSS_SELECTOR, ".fill-main")
            reservation.click()
            time.sleep(2)
        except Exception as e:
            print(f"[{self.actor_id}번] 영화 선택 중 오류: {e}")
            return False

        try:
            target = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//button[contains(., '{self.region}')]"))
                )
            target.click()
            time.sleep(1)

            select = self.driver.find_element(By.CSS_SELECTOR, ".fill-black")
            select.click()
            time.sleep(2)
        except:
            return False

        return True

    # ── [수정] start_movie_index → movie_name, while True 인덱스 증가 루프 제거 ──
    def process_all_times(self, movie_name, total_threads):
        CGV_TICKET_TYPES = {"일반", "대학생", "경로", "장애인", "국가유공자"}
        TARGET_COUNT = sum(
            v for k, v in self.ticket_config.items() if k in CGV_TICKET_TYPES
        )
        if TARGET_COUNT == 0:
            TARGET_COUNT = sum(self.ticket_config.values())

        if not self.select_movie_and_theater(movie_name):
            print(f"[{self.actor_id}번] 영화/극장 선택 실패. 스레드를 종료합니다.")
            return

        try:
            time_btns_initial = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//button[.//span[contains(text(),':')]]"))
                )

            valid_indices = []
            for idx, btn in enumerate(time_btns_initial):
                if not btn.get_attribute("disabled"):
                    valid_indices.append(idx)

            total_times = len(valid_indices)
            if total_times == 0:
                print(f"[{self.actor_id}번] 상영 시간표가 없습니다. 스레드를 종료합니다.")
                return

            # 전체 예매표(예매 시간대)를 스레드 개수만큼 균등 분할해서 크롤링을 분배해요
            chunk_size = math.ceil(total_times / total_threads)
            start_idx  = self.actor_id * chunk_size
            end_idx    = min(start_idx + chunk_size, total_times)

            if start_idx >= total_times:
                print(f"[{self.actor_id}번] 할당된 시간대가 없습니다.")
                return

            print(f"▶ [{self.actor_id}번 스레드] 총 {total_times}개 중 {start_idx + 1}~{end_idx}번째 시간대 처리 담당 (영화: {movie_name})")

            for i in range(start_idx, end_idx):
                target_btn_idx = valid_indices[i]
                target_btn     = None
                time_text      = ""

                for attempt in range(3):
                    try:
                        time.sleep(1.5)
                        time_btns  = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_all_elements_located(
                                (By.XPATH, "//button[.//span[contains(text(),':')]]"))
                            )
                        target_btn = time_btns[target_btn_idx]
                        time_text  = target_btn.text.replace('\n', ' ').strip()
                        if not time_text:
                            time_text = "(시간 텍스트 없음)"
                        break
                    except:
                        try:
                            tgt = self.driver.find_element(
                                By.XPATH, f"//button[contains(., '{self.region}')]")
                            self.driver.execute_script("arguments[0].click();", tgt)
                            time.sleep(2)
                        except:
                            pass

                if not target_btn:
                    continue

                print(f"\n==================================================")
                print(f"[{self.actor_id}번] 상영 시간: {time_text} 분석 시작")
                print(f"==================================================")

                self.driver.execute_script("arguments[0].scrollIntoView(true);", target_btn)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", target_btn)
                time.sleep(2)

                try:
                    alert = Alert(self.driver)
                    alert.accept()
                    time.sleep(1)
                except:
                    pass

                try:
                    unbookable_btns = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'fill-main') and text()='확인']")
                    for btn in unbookable_btns:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(1.5)
                            break
                except:
                    pass

                seat_screen_reached = False
                try:
                    counts = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "button[class*='btn-num']"))
                        )
                    for btn in counts:
                        if btn.text.strip() == str(TARGET_COUNT):
                            self.driver.execute_script("arguments[0].click();", btn)
                            break

                    time.sleep(0.5)
                    select_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), '선택')]")
                    for btn in select_btns:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            break

                    seat_screen_reached = True
                    time.sleep(2)
                except Exception as e:
                    print(f"[{self.actor_id}번] 인원/좌석 선택 화면 진입 실패: {e}")

                if seat_screen_reached:
                    self.analyze_seat(TARGET_COUNT, time_text)

                # 좌석 선택 모달 닫기
                try:
                    close_svg_xpath = "//*[local-name()='svg' and ./*[local-name()='path' and @d='M23 9L9 23M9 9L23 23']]"
                    time.sleep(1)
                    for svg in self.driver.find_elements(By.XPATH, close_svg_xpath):
                        if svg.is_displayed():
                            parent_btn = svg.find_element(By.XPATH, "..")
                            self.driver.execute_script("arguments[0].click();", parent_btn)
                            break
                    time.sleep(1)
                except:
                    pass

                try:
                    back_btn_xpath = "//button[@title='뒤로가기' and .//*[local-name()='path' and @d='M16 21L7 12L16 3']]"
                    time.sleep(0.5)
                    back_btns = self.driver.find_elements(By.XPATH, back_btn_xpath)
                    for btn in back_btns:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            break
                    time.sleep(1.5)
                except:
                    pass

            print(f"[{self.actor_id}번] 할당된 모든 시간대 분석이 완료되었습니다.")

        except Exception as e:
            print(f"[{self.actor_id}번] 치명적 오류 발생: {e}")

    def analyze_seat(self, required_seats, formatted_time):
        if required_seats == 0:
            return

        try:
            parent_container = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[class*='seatMap_seatPositionWrap']"))
                )
            available_seats = parent_container.find_elements(
                By.CSS_SELECTOR, "button[class*='seatNormal']:not([disabled])")

            seat_map = {}
            for seat in available_seats:
                seat_name  = seat.text
                style_str  = seat.get_attribute("style") or ""

                left_match = re.search(r"left:\s*([\d.]+)px", style_str)
                top_match  = re.search(r"top:\s*([\d.]+)px",  style_str)
                coords     = re.findall(r"[\d.]+", style_str)

                if left_match and top_match:
                    left   = float(left_match.group(1))
                    top    = float(top_match.group(1))
                    width, height = 20, 20
                elif len(coords) >= 4:
                    top, left, width, height = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
                else:
                    continue

                center_x = (left + width  / 2) / 722
                center_y = (top  + height / 2) / 570

                in_x = self.preferred_seat["x_start"] <= center_x <= self.preferred_seat["x_end"]
                in_y = self.preferred_seat["y_start"] <= center_y <= self.preferred_seat["y_end"]

                if in_x and in_y:
                    match = re.match(r"([A-Za-z]+)(\d+)", seat_name)
                    if match:
                        row = match.group(1)
                        col = int(match.group(2))
                        if row not in seat_map:
                            seat_map[row] = []
                        seat_map[row].append(col)

            sorted_rows = sorted(seat_map.keys())
            found_seats = []

            for row in sorted_rows:
                cols = sorted(seat_map[row])
                for col in cols:
                    found_seats.append(f"{row}{col}")

            total_seats = len(found_seats)

            print(f"--- [{self.actor_id}번 | {formatted_time}] 필터링 및 정렬된 좌석 목록 ---")
            for seat_str in found_seats:
                print(seat_str)
            print("-" * 30)
            print(f"총 추출된 좌석 수: {total_seats}개")

            with self.results_lock:
                self.results_list.append({
                    "showtime":        formatted_time,
                    "remaining_seats": None,
                    "seats":           found_seats,
                    "total":           len(found_seats),
                })

        except Exception as e:
            print(f"[{self.actor_id}번] 좌석 분석 중 오류 발생 (예매불가 좌석일 확률 높음): {e}")

    def close_browser(self):
        try:
            self.driver.quit()
        except:
            pass


# ── [수정] movie_index → movie_name ──────────────────────────────────────────
def thread_worker(actor_id, movie_name, total_threads,
                  region, ticket_config, preferred_seat,
                  results_list, results_lock, error_event):
    actor = CGVActor(actor_id, region, ticket_config, preferred_seat,
                     results_list, results_lock, error_event)
    actor.process_all_times(movie_name, total_threads)
    actor.close_browser()


# server.py 진입점
def run_cgv(params: dict) -> dict:
    movie_name     = params.get("movie_name",     "")         # ← movie_index → movie_name
    region         = params.get("region",         "강남")
    ticket_config  = params.get("ticket_config",  {"일반": 1})
    preferred_seat = params.get("preferred_seat", {"x_start": 0.0, "x_end": 1.0,
                                                   "y_start": 0.0, "y_end": 1.0})
    num_workers    = params.get("num_workers",    3)

    theater = params.get("theater", "")
    if theater:
        region = theater

    if not movie_name:
        return {
            "cinema":    "cgv",
            "theater":   region,
            "status":    "error",
            "message":   "movie_name이 비어있습니다.",
            "showtimes": [],
        }

    final_results = []
    result_lock   = threading.Lock()
    error_event   = threading.Event()   # 영화 미발견 플래그

    threads = []
    for i in range(num_workers):
        t = threading.Thread(
            target=thread_worker,
            args=(i, movie_name, num_workers,
                  region, ticket_config, preferred_seat,
                  final_results, result_lock, error_event),
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # 영화를 찾지 못한 경우 에러 응답 반환
    if error_event.is_set():
        return {
            "cinema":    "cgv",
            "theater":   region,
            "status":    "error",
            "message":   f"'{movie_name}'에 해당하는 영화를 CGV 목록에서 찾지 못했습니다.",
            "showtimes": [],
        }

    final_results.sort(key=lambda x: x["showtime"])

    return {
        "cinema":    "cgv",
        "theater":   region,
        "status":    "success",
        "showtimes": final_results,
    }