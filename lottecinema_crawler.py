# 크롤링 테스트
# (01.12 수정사항) prefs 변수 만들어 위치 정보 권한 강제로 차단하는 코드 만들었습니다. 제 환경 문제 때문에 만든거니 종민님 테스트 환경에서는 필요할때 쓰면 될거예요.
# ㄴ 참고한 링크 - https://velog.io/@sangyeon217/mocking-geolocation
# v1.1.0 수정사항 - 주요 기능: 예매표 순회 기능, 멀티스레딩 추가
# v1.2.0 수정사항 - movie_index → movie_name 기반 매칭으로 변경
#   공백 제거 + 소문자 변환 후 in 연산자로 유연하게 매칭
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
import threading
import time
import re
import math

# ======================계정 정보====================
LOTTECINEMA_ID = "dlwhdals6093@naver.com"
LOTTECINEMA_PW = "jongmin0329!"

#전역변수 삭제하고 생성자로 설정
class LotteActor:
    def __init__(self, actor_id, region, theater, ticket_config, preferred_seat,
                 results_list, results_lock, error_event):
        self.actor_id       = actor_id
        self.region         = region
        self.theater        = theater
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
        self.driver.maximize_window()
        self.is_logged_in = self.login()

    def login(self):
        print(f"[{self.actor_id}번] 롯데시네마 접속 및 로그인 진행")
        self.driver.get("https://www.lottecinema.co.kr/NLCHS/Member/login")
        try:
            id_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "userId"))
                )
            id_input.click()
            id_input.clear()
            id_input.send_keys(LOTTECINEMA_ID)

            pw_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "userPassword"))
                )
            pw_input.click()
            pw_input.clear()
            pw_input.send_keys(LOTTECINEMA_PW)
            time.sleep(1)

            login_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn_login"))
                )
            login_btn.click()
            time.sleep(4)
            return True
        except Exception as e:
            print(f"[{self.actor_id}번] 로그인 실패 (해당 스레드를 종료합니다): {e}")
            return False

    # ── [수정] movie_index → movie_name 기반 매칭 ──────────────────────────
    def select_movie_and_theater(self, movie_name):
        self.driver.get("https://www.lottecinema.co.kr/NLCHS/Ticketing")
        time.sleep(3)

        # 영화 선택 — 이름 기반 매칭
        try:
            movie_list = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".movie_select_wrap.list.movieSelect ul li a"))
                )

            # 공백 제거 + 소문자 변환 후 in 연산자로 유연하게 매칭
            target_norm = movie_name.replace(" ", "").lower()
            target = None
            for item in movie_list:
                item_norm = item.text.replace(" ", "").lower()
                if target_norm in item_norm or item_norm in target_norm:
                    target = item
                    break

            if target is None:
                print(f"[{self.actor_id}번] '{movie_name}'과 매칭되는 영화를 롯데시네마 목록에서 찾지 못했습니다.")
                self.error_event.set()
                return False

            self.driver.execute_script("arguments[0].click();", target)
            time.sleep(1)
        except Exception as e:
            print(f"[{self.actor_id}번] 영화 선택 중 오류: {e}")
            return False

        # 극장 선택
        try:
            region_xpath = f"//div[contains(@class, 'cinema_select_wrap')]//li[contains(@class, 'depth1')]/a[contains(text(), '{self.region}')]"
            region_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, region_xpath))
                )
            self.driver.execute_script("arguments[0].click();", region_btn)
            time.sleep(0.5)

            theater_xpath = f"//li[contains(@class, 'depth1') and contains(@class, 'active')]//div[contains(@class, 'depth2')]//a[text()='{self.theater}']"
            theater_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, theater_xpath))
                )
            self.driver.execute_script("arguments[0].click();", theater_btn)
            time.sleep(2)
        except:
            return False

        return True

    # ── [수정] start_movie_index → movie_name, while True 인덱스 증가 루프 제거 ──
    def process_all_times(self, movie_name, total_threads):
        LOTTE_TICKET_TYPES = {"성인", "청소년", "경로", "장애인", "국가유공자"}
        TARGET_COUNT = sum(
            v for k, v in self.ticket_config.items() if k in LOTTE_TICKET_TYPES
        )
        if TARGET_COUNT == 0:
            TARGET_COUNT = sum(self.ticket_config.values())

        if not self.select_movie_and_theater(movie_name):
            print(f"[{self.actor_id}번] 영화/극장 선택 실패. 스레드를 종료합니다.")
            return

        try:
            time_xpath = "//a[@role='button' and .//dd[contains(@class,'time')]]"
            time_elements_initial = self.driver.find_elements(By.XPATH, time_xpath)

            valid_indices = []
            for idx, t in enumerate(time_elements_initial):
                try:
                    if t.is_displayed():
                        class_attr = t.get_attribute("class") or ""
                        if "disabled" not in class_attr and "soldout" not in class_attr:
                            valid_indices.append(idx)
                except:
                    continue

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
                btn_idx = valid_indices[i]
                time.sleep(1.5)
                time_elements = self.driver.find_elements(By.XPATH, time_xpath)

                if btn_idx >= len(time_elements):
                    continue

                target_btn = time_elements[btn_idx]
                try:
                    start_time = target_btn.find_element(By.CSS_SELECTOR, "dd.time strong").text
                    rest_seat  = target_btn.find_element(By.CSS_SELECTOR, "dd.seat strong").text
                except:
                    continue

                print("\n==================================================")
                print(f"[{self.actor_id}번] 상영 시간: {start_time} (잔여 {rest_seat}석) 분석 시작")
                print("==================================================")

                self.driver.execute_script("arguments[0].scrollIntoView(true);", target_btn)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", target_btn)
                time.sleep(1)

                try:
                    alert = Alert(self.driver)
                    alert.accept()
                    time.sleep(0.5)
                except:
                    pass

                # 안내창 닫기
                try:
                    popup_btns = self.driver.find_elements(By.CSS_SELECTOR, "button.btn_close.btnCloseLayerMulti")
                    for btn in popup_btns:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(0.5)
                except:
                    pass

                # 두 번째 '인원/좌석 선택' 버튼 클릭
                try:
                    next_step_xpath = "//a[contains(@class,'btn_col1') and contains(text(),'인원/좌석 선택')]"
                    next_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, next_step_xpath))
                        )
                    self.driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(2)
                except:
                    try:
                        step1_tab = self.driver.find_element(By.CSS_SELECTOR, "li.step01 > a")
                        self.driver.execute_script("arguments[0].click();", step1_tab)
                    except:
                        pass
                    continue

                # 인원 설정
                for ticket_type, count in self.ticket_config.items():
                    if count == 0:
                        continue
                    selector = f"li[data-peple='{ticket_type}'] button.btn_plus"
                    try:
                        cnt_btn = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        for _ in range(count):
                            self.driver.execute_script("arguments[0].click();", cnt_btn)
                            time.sleep(0.3)
                    except:
                        pass

                remaining = int(rest_seat) if rest_seat.isdigit() else None
                self.analyze_seat(TARGET_COUNT, start_time, remaining)

                try:
                    step1_tab = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "li.step01 > a"))
                        )
                    self.driver.execute_script("arguments[0].click();", step1_tab)
                    time.sleep(1.5)
                except:
                    pass

            print(f"[{self.actor_id}번] 할당된 모든 시간대 분석이 완료되었습니다.")

        except Exception as e:
            print(f"[{self.actor_id}번] 시간 순차 분석 중 오류 발생: {e}")

    def analyze_seat(self, required_seats, formatted_time, remaining_seats=None):
        if required_seats == 0:
            return

        time.sleep(1)
        try:
            seat_container = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "seat_area"))
                )

            container_width  = seat_container.size['width']
            container_height = seat_container.size['height']
            all_seats = seat_container.find_elements(By.CSS_SELECTOR, "a.sel")

            seat_map = {}
            for seat in all_seats:
                if seat.get_attribute("seat-statuscode") != "0":
                    continue

                style_str  = seat.get_attribute("style") or ""
                left_match = re.search(r"left:\s*([\d.]+)px", style_str)
                top_match  = re.search(r"top:\s*([\d.]+)px",  style_str)

                if left_match and top_match and container_width > 0 and container_height > 0:
                    left  = float(left_match.group(1))
                    top   = float(top_match.group(1))

                    rel_x = left / container_width
                    rel_y = top  / container_height

                    in_x = self.preferred_seat["x_start"] <= rel_x <= self.preferred_seat["x_end"]
                    in_y = self.preferred_seat["y_start"] <= rel_y <= self.preferred_seat["y_end"]

                    if not (in_x and in_y):
                        continue

                seat_id = seat.get_attribute("data-seat")
                if not seat_id: continue

                match = re.match(r"([A-Za-z]+)(\d+)", seat_id)
                if match:
                    row = match.group(1)
                    col = int(match.group(2))
                    if row not in seat_map:
                        seat_map[row] = []
                    seat_map[row].append(col)

            sorted_rows = sorted(seat_map.keys())
            total_seats = sum(len(cols) for cols in seat_map.values())

            found_seats = []

            print(f"--- [{self.actor_id}번 | {formatted_time}] 필터링 및 정렬된 좌석 목록 ---")
            for row in sorted_rows:
                sorted_cols = sorted(seat_map[row])
                for col in sorted_cols:
                    seat_name = f"{row}{col}"
                    found_seats.append(seat_name)
                    print(seat_name)

            print("-" * 30)
            print(f"총 추출된 좌석 수: {total_seats}개")

            with self.results_lock:
                self.results_list.append({
                    "showtime":        formatted_time,
                    "remaining_seats": remaining_seats,
                    "seats":           found_seats,
                    "total":           len(found_seats),
                })

        except Exception as e:
            print(f"[{self.actor_id}번] 좌석 분석 중 오류 발생: {e}")

    def close_browser(self):
        try:
            self.driver.quit()
        except:
            pass


# ── [수정] movie_index → movie_name ──────────────────────────────────────────
def thread_worker(actor_id, movie_name, total_threads,
                  region, theater, ticket_config, preferred_seat,
                  results_list, results_lock, error_event):
    actor = LotteActor(actor_id, region, theater, ticket_config, preferred_seat,
                       results_list, results_lock, error_event)
    if actor.is_logged_in:
        actor.process_all_times(movie_name, total_threads)
    actor.close_browser()


# server.py 진입점
def run_lottecinema(params: dict) -> dict:
    movie_name     = params.get("movie_name",     "")         # ← movie_index → movie_name
    region         = params.get("region",         "서울")
    theater        = params.get("theater",        "")
    ticket_config  = params.get("ticket_config",  {"성인": 2})
    preferred_seat = params.get("preferred_seat", {"x_start": 0.0, "x_end": 1.0,
                                                   "y_start": 0.0, "y_end": 1.0})
    num_workers    = params.get("num_workers",    3)

    if not movie_name:
        return {
            "cinema":    "lottecinema",
            "theater":   theater,
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
                  region, theater, ticket_config, preferred_seat,
                  final_results, result_lock, error_event),
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # 영화를 찾지 못한 경우 에러 응답 반환
    if error_event.is_set():
        return {
            "cinema":    "lottecinema",
            "theater":   theater,
            "status":    "error",
            "message":   f"'{movie_name}'에 해당하는 영화를 롯데시네마 목록에서 찾지 못했습니다.",
            "showtimes": [],
        }

    final_results.sort(key=lambda x: x["showtime"])

    return {
        "cinema":    "lottecinema",
        "theater":   theater,
        "status":    "success",
        "showtimes": final_results,
    }