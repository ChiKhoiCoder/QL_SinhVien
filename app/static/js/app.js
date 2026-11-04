const backdrop = document.getElementById('modal-backdrop');
const modalBody = document.getElementById('modal-body');
const modalTitle = document.getElementById('modal-title');

function openModal(title, content) {
  modalTitle.textContent = title;
  modalBody.innerHTML = content;
  backdrop.classList.add('open');
}
function closeModal() { backdrop.classList.remove('open'); }
function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function field(label, name, value = '', type = 'text', extra = '') {
  return `<div class="field"><label for="f-${name}">${label}</label><input id="f-${name}" name="${name}" type="${type}" value="${esc(value)}" ${extra}></div>`;
}
function selectField(label, name, options, selected = '') {
  return `<div class="field"><label for="f-${name}">${label}</label><select id="f-${name}" name="${name}">${options.map(o => `<option value="${esc(o.value)}" ${String(o.value) === String(selected ?? '') ? 'selected' : ''}>${esc(o.label)}</option>`).join('')}</select></div>`;
}
function studentClassOptions(selected) {
  const options = [{value:'',label:'Không xếp lớp'}, ...(window.classOptions || []).map(c => ({value:c.id,label:`${c.code} — ${c.name}`}))];
  return selectField('Lớp học', 'class_id', options, selected);
}
function studentForm(student = {}) {
  const body = `<form method="post" action="/students/save"><input type="hidden" name="id" value="${esc(student.id || '')}"><div class="form-grid">${field('Mã sinh viên *','code',student.code,'text','required')}${field('Họ và tên *','full_name',student.full_name,'text','required')}${field('Ngày sinh','birth_date',student.birth_date,'date')}${selectField('Giới tính','gender',[{value:'',label:'Chọn giới tính'},...['Nam','Nữ','Khác'].map(x=>({value:x,label:x}))],student.gender)}${field('Số điện thoại','phone',student.phone,'tel')}${field('Email','email',student.email,'email')}${field('Địa chỉ','address',student.address)}${field('Ngành học','major',student.major)}<div class="field">${studentClassOptions(student.class_id).replace(/^<div class="field">|<\/div>$/g,'')}</div></div><div class="modal-actions"><button type="button" class="button subtle" onclick="closeModal()">Hủy</button><button class="button primary">Lưu thông tin</button></div></form>`;
  openModal(student.id ? 'Cập nhật sinh viên' : 'Thêm sinh viên mới', body);
}
function openStudentModal(student = {}) { studentForm(student); }
function openClassModal(cls = {}) {
  const body = `<form method="post" action="/classes/save"><input type="hidden" name="id" value="${esc(cls.id || '')}"><div class="form-grid">${field('Mã lớp *','code',cls.code,'text','required')}${field('Tên lớp *','name',cls.name,'text','required')}${field('Ngành học','major',cls.major)}${field('Giáo viên chủ nhiệm','homeroom_teacher',cls.homeroom_teacher)}</div><div class="modal-actions"><button type="button" class="button subtle" onclick="closeModal()">Hủy</button><button class="button primary">Lưu thông tin</button></div></form>`;
  openModal(cls.id ? 'Cập nhật lớp học' : 'Thêm lớp học', body);
}
function openGradeModal(grade = {}) {
  const students = window.studentOptions || [];
  const studentSelect = selectField('Sinh viên *','student_id',[{value:'',label:'Chọn sinh viên'},...students.map(s=>({value:s.id,label:`${s.code} — ${s.full_name}`}))],grade.student_id);
  const body = `<form method="post" action="/grades/save"><input type="hidden" name="id" value="${esc(grade.id || '')}"><div class="form-grid"><div class="field full">${studentSelect.replace(/^<div class="field">|<\/div>$/g,'')}</div>${field('Môn học *','subject',grade.subject,'text','required')}${field('Học kỳ','semester',grade.semester || 'Học kỳ 1')}${field('Điểm (0–10) *','score',grade.score,'number','required min="0" max="10" step="0.1"')}</div><div class="modal-actions"><button type="button" class="button subtle" onclick="closeModal()">Hủy</button><button class="button primary">Lưu điểm</button></div></form>`;
  openModal(grade.id ? 'Cập nhật điểm' : (grade.student_name ? `Nhập điểm — ${grade.student_name}` : 'Thêm điểm mới'), body);
}
function openSubjectModal(subject = {}) {
  const body = `<form method="post" action="/subjects/save"><input type="hidden" name="id" value="${esc(subject.id || '')}"><div class="form-grid">${field('Mã môn *','code',subject.code,'text','required')}${field('Tên môn học *','name',subject.name,'text','required')}${field('Ngành học','major',subject.major)}${field('Số tín chỉ','credits',subject.credits || 3,'number','required min="1" max="12"')}</div><div class="modal-actions"><button type="button" class="button subtle" onclick="closeModal()">Hủy</button><button class="button primary">Lưu môn học</button></div></form>`;
  openModal(subject.id ? 'Cập nhật môn học' : 'Thêm môn học', body);
}
function openAttendanceModal(attendance = {}) {
  const students = window.studentOptions || [];
  const subjects = window.subjectOptions || [];
  const studentSelect = selectField('Sinh viên *','student_id',[{value:'',label:'Chọn sinh viên'},...students.map(s=>({value:s.id,label:`${s.code} — ${s.full_name}`}))],attendance.student_id);
  const subjectSelect = selectField('Môn học','subject_id',[{value:'',label:'Không chọn môn'},...subjects.map(s=>({value:s.id,label:`${s.code} — ${s.name}`}))],attendance.subject_id);
  const statusSelect = selectField('Trạng thái *','status',['Có mặt','Vắng','Muộn','Có phép'].map(x=>({value:x,label:x})),attendance.status || 'Có mặt');
  const body = `<form method="post" action="/attendance/save"><input type="hidden" name="id" value="${esc(attendance.id || '')}"><div class="form-grid"><div class="field full">${studentSelect.replace(/^<div class="field">|<\/div>$/g,'')}</div><div class="field full">${subjectSelect.replace(/^<div class="field">|<\/div>$/g,'')}</div>${field('Ngày điểm danh *','attendance_date',attendance.attendance_date || window.attendanceToday || new Date().toISOString().slice(0,10),'date','required')}<div class="field">${statusSelect.replace(/^<div class="field">|<\/div>$/g,'')}</div>${field('Ghi chú','note',attendance.note)}</div><div class="modal-actions"><button type="button" class="button subtle" onclick="closeModal()">Hủy</button><button class="button primary">Lưu điểm danh</button></div></form>`;
  openModal(attendance.id ? 'Cập nhật điểm danh' : (attendance.student_name ? `Điểm danh — ${attendance.student_name}` : 'Ghi điểm danh'), body);
}
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.settings-form').forEach(form => {
    form.addEventListener('change', event => {
      if (!form.classList.contains('appearance-form')) return;
      const data = new FormData(form);
      const color = data.get('accent_color') || 'blue';
      const theme = data.get('theme') || 'light';
      const preview = document.body;
      preview.classList.remove('accent-blue','accent-green','accent-violet','accent-orange','accent-rose','theme-light','theme-dark');
      preview.classList.add(`accent-${color}`,`theme-${theme}`);
      if (event.target.name === 'compact_tables') preview.classList.toggle('compact-tables',event.target.checked);
      if (event.target.name === 'show_dashboard_banner') {
        const banner=document.querySelector('.welcome-banner');
        if (banner) banner.style.display=event.target.checked?'flex':'none';
      }
    });
  });
});
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeModal(); });
