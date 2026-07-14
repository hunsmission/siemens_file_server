from flask import Flask, render_template, send_file, request, abort, jsonify, redirect, url_for, session
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
import uuid
import shutil
import json
import threading
import time
import zipfile
import tempfile

def safe_filename(filename):
    """한글 등 유니코드 문자를 보존하면서 파일명을 안전하게 정제합니다."""
    # 경로 구분자 및 위험 문자 제거
    filename = os.path.basename(filename)
    # Windows/Unix 파일명에서 금지된 문자 제거: \ / : * ? " < > |  그리고 제어문자
    filename = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', filename)
    # 선행/후행 공백 및 점 제거 (Windows 호환성)
    filename = filename.strip('. ')
    # 빈 문자열이면 fallback
    if not filename:
        return None
    return filename


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 * 1024  # 최대 50GB
app.secret_key = os.urandom(24)  # 세션 암호화 키

# 공유할 파일들이 있는 루트 디렉토리 경로 설정
ROOT_DIRECTORY = r"C:\Siemens"  # 원하는 경로로 변경하세요
TEMP_DIRECTORY = os.path.join(ROOT_DIRECTORY, ".upload_temp")  # 임시 업로드 폴더

# Werkzeug 업로드 버퍼 위치를 ROOT_DIRECTORY와 같은 드라이브로 지정
# (미설정 시 C드라이브 시스템 Temp를 사용해 대용량 업로드 시 C드라이브 공간 부족 발생)
tempfile.tempdir = TEMP_DIRECTORY
TRASH_DIRECTORY = os.path.join(ROOT_DIRECTORY, ".trash")  # 휴지통 폴더
TRASH_LOG = os.path.join(ROOT_DIRECTORY, ".trash_log.json")  # 삭제 기록 파일
MEMO_FILE = os.path.join(ROOT_DIRECTORY, ".memos.json")  # 메모 파일

# 폴더 생성
os.makedirs(TEMP_DIRECTORY, exist_ok=True)
os.makedirs(TRASH_DIRECTORY, exist_ok=True)

# 휴지통 관리 함수들
def load_trash_log():
    """휴지통 로그 파일 읽기"""
    if os.path.exists(TRASH_LOG):
        try:
            with open(TRASH_LOG, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_trash_log(log_data):
    """휴지통 로그 파일 저장"""
    with open(TRASH_LOG, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

def add_to_trash(item_path, original_path):
    """휴지통에 아이템 추가"""
    trash_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    delete_after = (datetime.now() + timedelta(days=1)).isoformat()

    is_dir = os.path.isdir(item_path)

    # 휴지통으로 이동
    trash_item_path = os.path.join(TRASH_DIRECTORY, trash_id)

    if is_dir:
        shutil.copytree(item_path, trash_item_path)
        shutil.rmtree(item_path)
    else:
        shutil.copy2(item_path, trash_item_path)
        os.remove(item_path)

    # 로그에 기록
    log_data = load_trash_log()
    log_data.append({
        'id': trash_id,
        'original_path': original_path,
        'original_name': os.path.basename(item_path),
        'is_dir': is_dir,
        'deleted_at': timestamp,
        'delete_after': delete_after,
        'trash_path': trash_item_path
    })
    save_trash_log(log_data)

    return trash_id

def cleanup_old_trash():
    """1일이 지난 휴지통 항목 삭제"""
    log_data = load_trash_log()
    now = datetime.now()
    updated_log = []

    for item in log_data:
        delete_after = datetime.fromisoformat(item['delete_after'])

        if now >= delete_after:
            # 삭제 시간이 지남 - 영구 삭제
            trash_path = item['trash_path']
            try:
                if os.path.exists(trash_path):
                    if item['is_dir']:
                        shutil.rmtree(trash_path, ignore_errors=True)
                    else:
                        os.remove(trash_path)
                print(f"[휴지통] 영구 삭제: {item['original_name']}")
            except Exception as e:
                print(f"[휴지통] 삭제 오류: {item['original_name']} - {e}")
        else:
            # 아직 보관 기간 - 유지
            updated_log.append(item)

    save_trash_log(updated_log)

def restore_from_trash(trash_id):
    """휴지통에서 복원"""
    log_data = load_trash_log()
    item = None

    for i, entry in enumerate(log_data):
        if entry['id'] == trash_id:
            item = entry
            log_data.pop(i)
            break

    if not item:
        return False, "항목을 찾을 수 없습니다"

    trash_path = item['trash_path']
    if not os.path.exists(trash_path):
        return False, "휴지통 파일이 존재하지 않습니다"

    # 원래 위치로 복원
    restore_path = os.path.join(ROOT_DIRECTORY, item['original_path'])

    # 이미 같은 이름이 있으면 번호 추가
    if os.path.exists(restore_path):
        base_path = os.path.dirname(restore_path)
        name = os.path.basename(restore_path)

        if item['is_dir']:
            counter = 1
            while os.path.exists(restore_path):
                restore_path = os.path.join(base_path, f"{name}_{counter}")
                counter += 1
        else:
            name_without_ext, ext = os.path.splitext(name)
            counter = 1
            while os.path.exists(restore_path):
                restore_path = os.path.join(base_path, f"{name_without_ext}_{counter}{ext}")
                counter += 1

    # 복원
    try:
        if item['is_dir']:
            shutil.copytree(trash_path, restore_path)
            shutil.rmtree(trash_path)
        else:
            shutil.copy2(trash_path, restore_path)
            os.remove(trash_path)

        save_trash_log(log_data)
        return True, "복원되었습니다"
    except Exception as e:
        return False, f"복원 실패: {str(e)}"

def start_trash_cleanup_thread():
    """휴지통 정리 백그라운드 스레드 시작"""
    def cleanup_loop():
        while True:
            try:
                cleanup_old_trash()
            except Exception as e:
                print(f"[휴지통] 정리 오류: {e}")

            # 1시간마다 실행
            time.sleep(3600)

    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    print("[휴지통] 자동 정리 스레드 시작됨 (1시간 간격)")

def get_item_info(filepath, relative_path=""):
    """파일/폴더 정보를 반환합니다"""
    stats = os.stat(filepath)
    size = stats.st_size
    is_dir = os.path.isdir(filepath)

    # 파일 크기를 읽기 쉽게 변환
    if is_dir:
        size_str = "-"
    else:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                size_str = f"{size:.1f} {unit}"
                break
            size = size / 1024.0
        else:
            size_str = f"{size:.1f} TB"

    # Windows 경로 구분자를 URL용 슬래시로 변환
    url_path = relative_path.replace('\\', '/')

    return {
        'name': os.path.basename(filepath),
        'path': url_path,
        'size': size_str,
        'size_bytes': stats.st_size,
        'modified': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'modified_ts': stats.st_mtime,
        'is_dir': is_dir
    }

def get_items_in_directory(directory, search_query=None):
    """디렉토리 내의 파일과 폴더 목록을 반환합니다"""
    items = []

    # 숨김 항목 목록 (시스템 폴더/파일)
    hidden_items = {'.trash', '.upload_temp', '.trash_log.json', '.memos.json'}

    try:
        for item in os.listdir(directory):
            # 시스템 폴더/파일 숨기기
            if item in hidden_items:
                continue

            item_path = os.path.join(directory, item)

            # 상대 경로 계산
            relative_path = os.path.relpath(item_path, ROOT_DIRECTORY)

            if search_query and search_query.lower() not in item.lower():
                continue

            items.append(get_item_info(item_path, relative_path))

        # 폴더 먼저, 그 다음 파일 (각각 이름순 정렬)
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    except Exception as e:
        print(f"Error reading directory: {e}")

    return items

@app.route('/')
@app.route('/browse/')
@app.route('/browse/<path:subpath>')
def browse(subpath=''):
    """파일 탐색 페이지"""
    search_query = request.args.get('search', '')

    # 현재 디렉토리 경로 (URL 경로를 Windows 경로로 변환)
    if subpath:
        # URL의 /를 Windows의 \로 변환
        subpath_normalized = subpath.replace('/', os.sep)
        current_dir = os.path.join(ROOT_DIRECTORY, subpath_normalized)
    else:
        current_dir = ROOT_DIRECTORY

    # 보안: 경로 조작 방지
    if not os.path.abspath(current_dir).startswith(os.path.abspath(ROOT_DIRECTORY)):
        abort(403)

    if not os.path.exists(current_dir):
        abort(404)

    if not os.path.isdir(current_dir):
        abort(400)

    # 아이템 목록 가져오기
    items = get_items_in_directory(current_dir, search_query)

    # 경로 breadcrumb 생성
    breadcrumbs = []
    if subpath:
        # URL에서 받은 경로는 /로 구분되어 있음
        parts = subpath.split('/')
        current_path = ""
        for part in parts:
            if not part:  # 빈 문자열 건너뛰기
                continue
            current_path = current_path + '/' + part if current_path else part
            breadcrumbs.append({
                'name': part,
                'path': current_path
            })

    return render_template('index.html',
                         items=items,
                         search_query=search_query,
                         current_path=subpath,
                         breadcrumbs=breadcrumbs)

@app.route('/download/<path:filepath>')
def download_file(filepath):
    """파일 다운로드"""
    try:
        # URL 경로를 Windows 경로로 변환
        filepath_normalized = filepath.replace('/', os.sep)
        file_path = os.path.join(ROOT_DIRECTORY, filepath_normalized)

        # 보안: 경로 조작 방지
        if not os.path.abspath(file_path).startswith(os.path.abspath(ROOT_DIRECTORY)):
            abort(403)

        if not os.path.exists(file_path):
            abort(404)

        # 폴더인 경우 ZIP으로 압축하여 다운로드
        if os.path.isdir(file_path):
            folder_name = os.path.basename(file_path)
            zip_filename = f"{folder_name}.zip"

            # 임시 ZIP 파일 생성
            temp_dir = tempfile.gettempdir()
            temp_zip_path = os.path.join(temp_dir, f"download_{uuid.uuid4().hex}.zip")

            print(f"[ZIP] 압축 시작: {folder_name}")

            # ZIP 파일 생성
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 폴더 내 모든 파일 추가
                for root, dirs, files in os.walk(file_path):
                    for file in files:
                        file_full_path = os.path.join(root, file)
                        # ZIP 내부 경로 계산
                        arcname = os.path.relpath(file_full_path, file_path)
                        zipf.write(file_full_path, arcname)

            print(f"[ZIP] 압축 완료: {temp_zip_path}")

            # Flask 버전 호환성 처리
            try:
                # Flask 2.0 이상
                response = send_file(
                    temp_zip_path,
                    as_attachment=True,
                    download_name=zip_filename,
                    mimetype='application/zip'
                )
            except TypeError:
                # Flask 1.x (download_name 대신 attachment_filename)
                response = send_file(
                    temp_zip_path,
                    as_attachment=True,
                    attachment_filename=zip_filename,
                    mimetype='application/zip'
                )

            # 응답 후 임시 파일 삭제 (백그라운드)
            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(temp_zip_path):
                        os.remove(temp_zip_path)
                        print(f"[ZIP] 임시 파일 삭제: {temp_zip_path}")
                except Exception as e:
                    print(f"[ZIP] 임시 파일 삭제 실패: {e}")

            return response
        else:
            # 파일인 경우 그대로 다운로드
            return send_file(file_path, as_attachment=True)

    except Exception as e:
        print(f"Error downloading file: {e}")
        abort(500)

@app.route('/api/items')
@app.route('/api/items/<path:subpath>')
def api_items(subpath=''):
    """파일/폴더 목록 API"""
    search_query = request.args.get('search', '')

    # URL 경로를 Windows 경로로 변환
    if subpath:
        subpath_normalized = subpath.replace('/', os.sep)
        current_dir = os.path.join(ROOT_DIRECTORY, subpath_normalized)
    else:
        current_dir = ROOT_DIRECTORY

    # 보안: 경로 조작 방지
    if not os.path.abspath(current_dir).startswith(os.path.abspath(ROOT_DIRECTORY)):
        abort(403)

    items = get_items_in_directory(current_dir, search_query)
    return jsonify(items)

@app.route('/upload_temp', methods=['POST'])
@app.route('/upload_temp/<path:subpath>', methods=['POST'])
def upload_temp(subpath=''):
    """임시 폴더에 파일 업로드"""
    try:
        # 파일 가져오기
        if 'files[]' not in request.files:
            return jsonify({'error': '파일이 선택되지 않았습니다'}), 400

        files = request.files.getlist('files[]')

        # 세션에 업로드 ID 생성
        if 'upload_id' not in session:
            session['upload_id'] = str(uuid.uuid4())

        upload_id = session['upload_id']
        user_temp_dir = os.path.join(TEMP_DIRECTORY, upload_id)
        os.makedirs(user_temp_dir, exist_ok=True)

        uploaded_files = []

        for file in files:
            if file.filename == '':
                continue

            # 원본 파일명 저장
            original_filename = file.filename
            cleaned_filename = safe_filename(original_filename)

            if not cleaned_filename:
                continue

            temp_file_path = os.path.join(user_temp_dir, cleaned_filename)

            # 임시 폴더에서도 중복 방지
            if os.path.exists(temp_file_path):
                name, ext = os.path.splitext(cleaned_filename)
                counter = 1
                while os.path.exists(temp_file_path):
                    cleaned_filename = f"{name}_{counter}{ext}"
                    temp_file_path = os.path.join(user_temp_dir, cleaned_filename)
                    counter += 1

            # 임시 폴더에 저장
            file.save(temp_file_path)

            # 파일 크기 계산
            file_size = os.path.getsize(temp_file_path)
            uploaded_files.append({
                'name': cleaned_filename,
                'original_name': original_filename,
                'size': file_size,
                'size_str': format_file_size(file_size)
            })

        # 세션에 대상 경로 저장
        session['target_path'] = subpath

        return jsonify({
            'success': True,
            'files': uploaded_files,
            'count': len(uploaded_files),
            'upload_id': upload_id
        })

    except Exception as e:
        print(f"Error uploading to temp: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/check_duplicates', methods=['POST'])
def check_duplicates():
    """임시 폴더의 파일 중 목적지에 이미 존재하는 파일 목록 반환"""
    try:
        if 'upload_id' not in session:
            return jsonify({'error': '업로드 세션이 없습니다'}), 400

        upload_id = session['upload_id']
        subpath = session.get('target_path', '')

        user_temp_dir = os.path.join(TEMP_DIRECTORY, upload_id)

        if not os.path.exists(user_temp_dir):
            return jsonify({'error': '임시 파일을 찾을 수 없습니다'}), 404

        if subpath:
            subpath_normalized = subpath.replace('/', os.sep)
            target_dir = os.path.join(ROOT_DIRECTORY, subpath_normalized)
        else:
            target_dir = ROOT_DIRECTORY

        if not os.path.abspath(target_dir).startswith(os.path.abspath(ROOT_DIRECTORY)):
            abort(403)

        duplicates = []
        for filename in os.listdir(user_temp_dir):
            dst_path = os.path.join(target_dir, filename)
            if os.path.exists(dst_path):
                duplicates.append(filename)

        return jsonify({'success': True, 'duplicates': duplicates})

    except Exception as e:
        print(f"Error checking duplicates: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/confirm_upload', methods=['POST'])
def confirm_upload():
    """임시 폴더의 파일을 최종 목적지로 이동
    overwrite_decisions: {filename: 'overwrite'|'rename'|새이름문자열}
    """
    try:
        if 'upload_id' not in session:
            return jsonify({'error': '업로드 세션이 없습니다'}), 400

        upload_id = session['upload_id']
        subpath = session.get('target_path', '')

        user_temp_dir = os.path.join(TEMP_DIRECTORY, upload_id)

        if not os.path.exists(user_temp_dir):
            return jsonify({'error': '임시 파일을 찾을 수 없습니다'}), 404

        # 최종 목적지 경로
        if subpath:
            subpath_normalized = subpath.replace('/', os.sep)
            target_dir = os.path.join(ROOT_DIRECTORY, subpath_normalized)
        else:
            target_dir = ROOT_DIRECTORY

        # 보안: 경로 조작 방지
        if not os.path.abspath(target_dir).startswith(os.path.abspath(ROOT_DIRECTORY)):
            abort(403)

        if not os.path.exists(target_dir):
            abort(404)

        data = request.get_json(silent=True) or {}
        overwrite_decisions = data.get('overwrite_decisions', {})

        moved_files = []

        for filename in os.listdir(user_temp_dir):
            src_path = os.path.join(user_temp_dir, filename)
            dst_path = os.path.join(target_dir, filename)
            final_filename = filename

            if os.path.exists(dst_path):
                decision = overwrite_decisions.get(filename, 'rename')

                if decision == 'overwrite':
                    # 덮어쓰기: 기존 파일 그대로 덮어씀
                    pass
                elif decision == 'rename':
                    # 자동 번호 추가
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(dst_path):
                        final_filename = f"{name}_{counter}{ext}"
                        dst_path = os.path.join(target_dir, final_filename)
                        counter += 1
                else:
                    # 사용자가 직접 입력한 새 이름
                    new_name = safe_filename(str(decision))
                    if new_name:
                        final_filename = new_name
                        dst_path = os.path.join(target_dir, final_filename)
                        # 새 이름도 충돌 시 번호 추가
                        if os.path.exists(dst_path):
                            name, ext = os.path.splitext(final_filename)
                            counter = 1
                            while os.path.exists(dst_path):
                                final_filename = f"{name}_{counter}{ext}"
                                dst_path = os.path.join(target_dir, final_filename)
                                counter += 1

            # 보안: 목적지 경로 검증
            if not os.path.abspath(dst_path).startswith(os.path.abspath(ROOT_DIRECTORY)):
                continue

            shutil.move(src_path, dst_path)
            moved_files.append(final_filename)

        # 임시 폴더 삭제
        shutil.rmtree(user_temp_dir, ignore_errors=True)

        # 세션 정리
        session.pop('upload_id', None)
        session.pop('target_path', None)

        return jsonify({
            'success': True,
            'moved': moved_files,
            'count': len(moved_files)
        })

    except Exception as e:
        print(f"Error confirming upload: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/cancel_upload', methods=['POST'])
def cancel_upload():
    """임시 폴더의 파일 삭제"""
    try:
        if 'upload_id' not in session:
            return jsonify({'success': True, 'message': '삭제할 파일이 없습니다'})

        upload_id = session['upload_id']
        user_temp_dir = os.path.join(TEMP_DIRECTORY, upload_id)

        if os.path.exists(user_temp_dir):
            shutil.rmtree(user_temp_dir, ignore_errors=True)

        # 세션 정리
        session.pop('upload_id', None)
        session.pop('target_path', None)

        return jsonify({'success': True, 'message': '업로드가 취소되었습니다'})

    except Exception as e:
        print(f"Error canceling upload: {e}")
        return jsonify({'error': str(e)}), 500

def format_file_size(size_bytes):
    """파일 크기를 읽기 쉽게 변환"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

@app.route('/mkdir', methods=['POST'])
@app.route('/mkdir/<path:subpath>', methods=['POST'])
def make_directory(subpath=''):
    """디렉터리 생성"""
    try:
        # 현재 디렉토리 경로
        if subpath:
            subpath_normalized = subpath.replace('/', os.sep)
            current_dir = os.path.join(ROOT_DIRECTORY, subpath_normalized)
        else:
            current_dir = ROOT_DIRECTORY

        # 보안: 경로 조작 방지
        if not os.path.abspath(current_dir).startswith(os.path.abspath(ROOT_DIRECTORY)):
            abort(403)

        if not os.path.exists(current_dir):
            abort(404)

        if not os.path.isdir(current_dir):
            abort(400)

        # 폴더명 가져오기
        data = request.get_json()
        folder_name = data.get('folder_name', '').strip()

        if not folder_name:
            return jsonify({'error': '폴더 이름을 입력해주세요'}), 400

        # 안전한 폴더명으로 변환
        folder_name = safe_filename(folder_name)
        if not folder_name:
            return jsonify({'error': '유효하지 않은 폴더 이름입니다'}), 400

        new_dir_path = os.path.join(current_dir, folder_name)

        # 폴더가 이미 존재하면 번호 추가
        if os.path.exists(new_dir_path):
            counter = 1
            while os.path.exists(new_dir_path):
                new_folder_name = f"{folder_name}_{counter}"
                new_dir_path = os.path.join(current_dir, new_folder_name)
                counter += 1
            folder_name = new_folder_name

        # 폴더 생성
        os.makedirs(new_dir_path)

        return jsonify({
            'success': True,
            'folder_name': folder_name
        })

    except Exception as e:
        print(f"Error creating directory: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete/<path:filepath>', methods=['POST'])
def delete_item(filepath):
    """파일/폴더 삭제 (휴지통으로 이동)"""
    try:
        # 파일 경로
        filepath_normalized = filepath.replace('/', os.sep)
        item_path = os.path.join(ROOT_DIRECTORY, filepath_normalized)

        # 보안: 경로 조작 방지
        if not os.path.abspath(item_path).startswith(os.path.abspath(ROOT_DIRECTORY)):
            abort(403)

        if not os.path.exists(item_path):
            return jsonify({'error': '파일 또는 폴더를 찾을 수 없습니다'}), 404

        # 시스템 폴더 삭제 방지
        item_name = os.path.basename(item_path)
        if item_name.startswith('.'):
            return jsonify({'error': '시스템 폴더는 삭제할 수 없습니다'}), 403

        # 휴지통으로 이동
        trash_id = add_to_trash(item_path, filepath_normalized)

        return jsonify({
            'success': True,
            'message': '휴지통으로 이동되었습니다 (24시간 후 영구 삭제)',
            'trash_id': trash_id
        })

    except Exception as e:
        print(f"Error deleting item: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/trash/list', methods=['GET'])
def list_trash():
    """휴지통 목록 조회"""
    try:
        log_data = load_trash_log()
        now = datetime.now()

        trash_items = []
        for item in log_data:
            delete_after = datetime.fromisoformat(item['delete_after'])
            time_remaining = delete_after - now

            trash_items.append({
                'id': item['id'],
                'name': item['original_name'],
                'original_path': item['original_path'],
                'is_dir': item['is_dir'],
                'deleted_at': item['deleted_at'],
                'hours_remaining': int(time_remaining.total_seconds() / 3600),
                'minutes_remaining': int((time_remaining.total_seconds() % 3600) / 60)
            })

        return jsonify({
            'success': True,
            'items': trash_items,
            'count': len(trash_items)
        })

    except Exception as e:
        print(f"Error listing trash: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/trash/restore/<trash_id>', methods=['POST'])
def restore_item(trash_id):
    """휴지통에서 복원"""
    try:
        success, message = restore_from_trash(trash_id)

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        print(f"Error restoring item: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/icon/<path:filename>')
def serve_icon(filename):
    """아이콘 파일 제공"""
    icon_dir = os.path.join(os.path.dirname(__file__), 'icon')
    return send_file(os.path.join(icon_dir, filename))

# 메모 관련 함수
def load_memos():
    if os.path.exists(MEMO_FILE):
        try:
            with open(MEMO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_memos(memos):
    with open(MEMO_FILE, 'w', encoding='utf-8') as f:
        json.dump(memos, f, ensure_ascii=False, indent=2)

@app.route('/memo')
def memo_page():
    """메모 페이지"""
    return render_template('memo.html')

@app.route('/api/memos', methods=['GET'])
def api_get_memos():
    """메모 목록 조회"""
    try:
        memos = load_memos()
        return jsonify({'success': True, 'memos': memos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/memos', methods=['POST'])
def api_create_memo():
    """메모 생성"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'error': '내용을 입력해주세요'}), 400

        memos = load_memos()
        memo_id = str(uuid.uuid4())
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        memo = {
            'id': memo_id,
            'title': title,
            'content': content,
            'created_at': now,
            'updated_at': now
        }
        memos.insert(0, memo)
        save_memos(memos)

        return jsonify({'success': True, 'memo': memo})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/memos/<memo_id>', methods=['PUT'])
def api_update_memo(memo_id):
    """메모 수정"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'error': '내용을 입력해주세요'}), 400

        memos = load_memos()
        for memo in memos:
            if memo['id'] == memo_id:
                memo['title'] = title
                memo['content'] = content
                memo['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_memos(memos)
                return jsonify({'success': True, 'memo': memo})

        return jsonify({'error': '메모를 찾을 수 없습니다'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/memos/<memo_id>', methods=['DELETE'])
def api_delete_memo(memo_id):
    """메모 삭제"""
    try:
        memos = load_memos()
        updated = [m for m in memos if m['id'] != memo_id]

        if len(updated) == len(memos):
            return jsonify({'error': '메모를 찾을 수 없습니다'}), 404

        save_memos(updated)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 서비스 시작 시 휴지통 정리 스레드 시작
    start_trash_cleanup_thread()

    # 시작 시 한 번 정리
    cleanup_old_trash()

    print(f"파일 서버 시작!")
    print(f"공유 디렉토리: {ROOT_DIRECTORY}")
    print(f"휴지통 디렉토리: {TRASH_DIRECTORY}")
    print(f"접속 주소: http://localhost:8181")
    print(f"다른 PC에서 접속: http://<이 PC의 IP>:8181")

    app.run(host='0.0.0.0', port=8181, debug=True)
