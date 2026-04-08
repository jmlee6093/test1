# 크롤링 테스트
# (01.12 수정사항) prefs 변수 만들어 위치 정보 권한 강제로 차단하는 코드 만들었습니다. 제 환경 문제 때문에 만든거니 종민님 테스트 환경에서는 필요할때 쓰면 될거예요.
# ㄴ 참고한 링크 - https://velog.io/@sangyeon217/mocking-geolocation
# v1.1.0 수정사항 - 주요 기능: 예매표 순회 기능, 멀티스레딩 추가
# v1.2.0 수정사항 - movie_index → movie_name 기반 매칭으로 변경
#   공백 제거 + 소문자 변환 후 in 연산자로 유연하게 매칭
#   메가박스는 button[movie-nm] 속성값을 우선 사용해 매칭
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import time
import re
import math

# ======================계정 정보====================
MEGABOX_ID = "jmlee6093"
MEGABOX_PW = "jongmin0329!"

#전역변수 삭제하고 생성자로 설정
class MegaboxActor:
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
        self.driver.set_window_size(960, 520)

        self.login()

    def login(self):
        self.driver.get("https://www.megabox.co.kr/")
        try:
            login_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "로그인"))
                )
            login_link.click()
        except:
            self.driver.find_element(By.CSS_SELECTOR, ".link-login").click()
        time.sleep(1)

        id_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "ibxLoginId"))
            )
        id_input.click()
        id_input.clear()
        id_input.send_keys(MEGABOX_ID)
        time.sleep(1)

        pw_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "ibxLoginPwd"))
            )
        pw_input.click()
        pw_input.clear()
        pw_input.send_keys(MEGABOX_PW)
        time.sleep(1)

        login_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "btnLogin"))
            )
        login_btn.click()
        time.sleep(3)

    # ── [수정] movie_index → movie_name 기반 매칭 ──────────────────────────
    def select_movie(self, movie_name):
        try:
            # button[movie-nm] 전체 목록을 가져온 뒤 이름 기반으로 매칭
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button[movie-nm]"))
            )
            movie_btns = self.driver.find_elements(By.CSS_SELECTOR, "button[movie-nm]")

            # 공백 제거 + 소문자 변환 후 in 연산자로 유연하게 매칭
            # 메가박스는 movie-nm 속성값을 우선 사용하고, 없으면 버튼 텍스트로 대체
            target_norm = movie_name.replace(" ", "").lower()
            target = None
            for btn in movie_btns:
                raw = btn.get_attribute("movie-nm") or btn.text
                btn_norm = raw.replace(" ", "").lower()
                if target_norm in btn_norm or btn_norm in target_norm:
                    target = btn
                    break

            if target is None:
                print(f"[{self.actor_id}번] '{movie_name}'과 매칭되는 영화를 메가박스 목록에서 찾지 못했습니다.")
                self.error_event.set()
                return False

            self.driver.execute_script("arguments[0].click();", target)
            time.sleep(1)
            return True
        except Exception as e:
            print(f"[{self.actor_id}번] 영화 선택 오류: {e}")
            return False

    def select_theater(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//button[contains(., '{self.region}')]"))
                )
            self.find_element_simple(
                f"//button[contains(., '{self.region}')]", self.region)
            time.sleep(0.5)
            if not self.find_element_simple(
                    f"//button[contains(., '{self.theater}')]", self.theater):
                print(f"[{self.actor_id}번] {self.theater} 지점 없음.")
                return False
            return True
        except:
            print(f"[{self.actor_id}번] {self.region} 지역 버튼 못 찾음.")
            return False

    def check_no_schedule_popup(self):
        try:
            popups = self.driver.find_elements(By.XPATH, "//p[contains(@class,'txt-common') and contains(.,'해당 일자에 상영 시간표가 없습니다')]")

            is_popup_visible = False
            for p in popups:
                if p.is_displayed():
                    is_popup_visible = True
                    break

            if is_popup_visible:
                close_btns = self.driver.find_elements(By.CSS_SELECTOR, "button.btn-layer-close")
                for btn in close_btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)
                        return True
        except Exception:
            pass
        return False

    # ── [수정] start_movie_index → movie_name, while True 인덱스 증가 루프 제거 ──
    def process_all_times(self, movie_name, total_threads):
        self.driver.get("https://www.megabox.co.kr/booking")
        time.sleep(3)

        if not self.select_movie(movie_name):
            print(f"[{self.actor_id}번] 영화 선택 실패. 스레드를 종료합니다.")
            return

        time.sleep(1)

        if self.check_no_schedule_popup():
            print(f"[{self.actor_id}번] '{movie_name}' 시간표 없음 팝업 감지. 스레드를 종료합니다.")
            return

        if not self.select_theater():
            return
        time.sleep(2)

        times = self.driver.find_elements(By.CSS_SELECTOR, "button[play-start-time]")
        valid_times = [t for t in times if "disabled" not in t.get_attribute("class")]
        total_times = len(valid_times)

        if total_times == 0:
            print(f"[{self.actor_id}번] 화면에 표시된 예매 가능한 상영 시간이 없습니다.")
            return

        # 전체 예매표(예매 시간대)를 스레드 개수만큼 균등 분할해서 크롤링을 분배해요
        chunk_size = math.ceil(total_times / total_threads)
        start_idx  = self.actor_id * chunk_size
        end_idx    = min(start_idx + chunk_size, total_times)

        if start_idx >= total_times:
            print(f"[{self.actor_id}번] 할당된 시간대가 없습니다.")
            return

        print(f"▶ [{self.actor_id}번 스레드] 총 {total_times}개 중 {start_idx + 1}~{end_idx}번째 시간대 처리 담당 (영화: {movie_name})")

        for target_idx in range(start_idx, end_idx):
            self.driver.get("https://www.megabox.co.kr/booking")
            time.sleep(3)

            # 내부 순회마다 이름 기반 재선택
            self.select_movie(movie_name)
            time.sleep(1)
            self.check_no_schedule_popup()

            self.select_theater()
            time.sleep(2)

            times = self.driver.find_elements(By.CSS_SELECTOR, "button[play-start-time]")
            valid_times = [t for t in times if "disabled" not in t.get_attribute("class")]

            if target_idx >= len(valid_times):
                continue

            target_btn     = valid_times[target_idx]
            start_time     = target_btn.get_attribute("play-start-time")
            formatted_time = f"{start_time[:2]}:{start_time[2:]}"
            rest_seat      = target_btn.get_attribute("rest-seat-cnt")

            print("\n==================================================")
            print(f"[{self.actor_id}번] 상영 시간: {formatted_time} (잔여 {rest_seat}석) 분석 시작")
            print("==================================================")

            self.driver.execute_script("arguments[0].scrollIntoView(true);", target_btn)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", target_btn)

            self.close_popups()
            for _ in range(5):
                if self.close_last_popup_smart():
                    break
                time.sleep(1.5)

            select_success = self.select_ticket_count(self.ticket_config)
            if select_success:
                time.sleep(1)
                MBX_TICKET_TYPES = {"성인", "경로", "우대"}
                TARGET_COUNT = sum(
                    v for k, v in self.ticket_config.items() if k in MBX_TICKET_TYPES
                )
                if TARGET_COUNT == 0:
                    TARGET_COUNT = sum(self.ticket_config.values())
                remaining = int(rest_seat) if rest_seat and rest_seat.isdigit() else None
                self.analyze_seat_availability(TARGET_COUNT, formatted_time, remaining)
            else:
                print(f"[{self.actor_id}번] 인원 선택 실패")

        print(f"[{self.actor_id}번] 할당된 모든 시간대 분석이 완료되었습니다.")

    def select_ticket_count(self, ticket_config):
        ticket_titles = {
            "성인": "성인 좌석 선택 증가",
            "경로": "경로 좌석 선택 증가",
            "우대": "우대 좌석 선택 증가",
        }
        try:
            for ticket_type, count in ticket_config.items():
                if count == 0: continue

                # 메가박스가 지원하지 않는 티켓 종류(예: 청소년)는 건너뜀
                if ticket_type not in ticket_titles:
                    print(f"[{self.actor_id}번] '{ticket_type}' 티켓은 메가박스에서 지원하지 않아 건너뜁니다.")
                    continue

                target_title = ticket_titles[ticket_type]
                selector     = f"button.up[title='{target_title}']"

                btn = self.find_nth_element_smart(By.CSS_SELECTOR, selector, 0, 3)

                if btn:
                    for _ in range(count):
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                else:
                    return False
            return True
        except Exception as e:
            print(f"[{self.actor_id}번] 인원 설정 실패: {e}")
            return False

    def analyze_seat_availability(self, required_seats, formatted_time, remaining_seats=None):
        if required_seats == 0:
            return

        try:
            # 메가박스 좌석표는 iframe 내부에 존재해서 거기서 요소 찾아야해요.
            self.driver.switch_to.default_content()
            seat_frame = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "frameBokdMSeat"))
                )
            self.driver.switch_to.frame(seat_frame)
        except:
            return

        time.sleep(2)

        try:
            seat_container = self.driver.find_element(By.CLASS_NAME, "seat-layout")
            all_seats = seat_container.find_elements(By.TAG_NAME, "button")

            seat_map = {}

            for seat in all_seats:
                cls = seat.get_attribute("class")
                seat_title = seat.get_attribute("title")

                # 이미 예매됨, 장애인 좌석 등의 예매 불가 좌석을 걸러내요.
                if "finish" in cls or "impossible" in cls or "dim" in cls:
                    continue

                check_text = seat_title if seat_title else seat.text
                if "장애인" in check_text or "휠체어" in check_text:
                    continue

                style_str = seat.get_attribute("style")
                if style_str:
                    coords = re.findall(r"\d+", style_str)
                    if len(coords) >= 3:
                        left = int(coords[0])
                        top  = int(coords[1])
                        width  = int(coords[2])
                        height = 18
                        total_width  = 763
                        total_height = 150

                        center_x = (left + width / 2) / total_width
                        center_y = (top  + height / 2) / total_height
                    else:
                        continue
                else:
                    continue

                # 위에서 설정한 (0.0~1.0) 영역 내에 좌석의 중심점이 위치하는지 확인해요.
                if not (
                    self.preferred_seat["x_start"] <= center_x <= self.preferred_seat["x_end"]
                    and self.preferred_seat["y_start"] <= center_y <= self.preferred_seat["y_end"]
                ):
                    continue

                match = re.search(r"([A-Za-z]+)\s*(\d+)", check_text)
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
            print(f"[{self.actor_id}번] 좌석 분석 실패: {e}")

    def find_nth_element_smart(self, by, value, index, timeout):
        def try_find_nth(idx, t_out):
            try:
                WebDriverWait(self.driver, t_out).until(
                    EC.presence_of_all_elements_located((by, value))
                    )
                elements = self.driver.find_elements(by, value)
                return elements[idx] if len(elements) > idx else None
            except:
                return None

        self.driver.switch_to.default_content()
        result = try_find_nth(index, timeout)
        if result:
            return result

        for frame in self.driver.find_elements(By.TAG_NAME, "iframe"):
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                result = try_find_nth(index, 1)
                if result:
                    return result
            except:
                continue
        self.driver.switch_to.default_content()
        return None

    def find_element_simple(self, xpath, desc):
        try:
            el = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath)))
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except:
            el = self.find_nth_element_smart(By.XPATH, xpath, 0, desc)
            if el:
                self.driver.execute_script("arguments[0].click();", el)
                return True
        return False

    def close_popups(self):
        for _ in range(3):
            try:
                time.sleep(1)
                popup_btns = self.driver.find_elements(
                    By.CSS_SELECTOR, "button.button.purple.confirm")
                visible = [b for b in popup_btns if b.is_displayed()]
                if visible:
                    self.driver.execute_script("arguments[0].click();", visible[0])
                    time.sleep(1)
                else:
                    break
            except:
                break

    def close_last_popup_smart(self):
        target_selector = "button.button.purple.close-layer"

        def try_close():
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, target_selector)
                visible = [b for b in btns if b.is_displayed()]
                if visible:
                    self.driver.execute_script("arguments[0].click();", visible[0])
                    time.sleep(1)
                    return True
            except:
                pass
            return False

        self.driver.switch_to.default_content()
        if try_close(): return True

        for frame in self.driver.find_elements(By.TAG_NAME, "iframe"):
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                if try_close():
                    return True
            except:
                continue

        self.driver.switch_to.default_content()
        return False

    def close_browser(self):
        try:
            self.driver.quit()
        except Exception as e:
            pass


# ── [수정] movie_index → movie_name ──────────────────────────────────────────
def thread_worker(actor_id, movie_name, total_threads,
                  region, theater, ticket_config, preferred_seat,
                  results_list, results_lock, error_event):
    actor = MegaboxActor(actor_id, region, theater, ticket_config, preferred_seat,
                         results_list, results_lock, error_event)
    actor.process_all_times(movie_name, total_threads)
    actor.close_browser()


# server.py 진입점
def run_megabox(params: dict) -> dict:
    movie_name     = params.get("movie_name",     "")         # ← movie_index → movie_name
    region         = params.get("region",         "서울")
    theater        = params.get("theater",        "")
    ticket_config  = params.get("ticket_config",  {"성인": 2})
    preferred_seat = params.get("preferred_seat", {"x_start": 0.0, "x_end": 1.0,
                                                   "y_start": 0.0, "y_end": 1.0})
    num_workers    = params.get("num_workers",    3)

    if not movie_name:
        return {
            "cinema":    "megabox",
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
            "cinema":    "megabox",
            "theater":   theater,
            "status":    "error",
            "message":   f"'{movie_name}'에 해당하는 영화를 메가박스 목록에서 찾지 못했습니다.",
            "showtimes": [],
        }

    final_results.sort(key=lambda x: x["showtime"])

    return {
        "cinema":    "megabox",
        "theater":   theater,
        "status":    "success",
        "showtimes": final_results,
    }