"""Select useful QIPEDC candidates by clinic tasks, never by recognizer IDs.

This is an editorial priority list, not a measured frequency corpus. A source
record becomes usable only after motion, visual review and narration checks.
"""
import json
from pathlib import Path
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
GROUPS={
'Khám bệnh': 'đau bụng;đau chân;đau tay;đau mắt;đau tai;đau mắt đỏ;chữa bệnh;điều trị;khỏi bệnh;bệnh tật;bệnh nhân;băng bó;cấp cứu;xe cứu thương;trạm y tế;phòng y tế;phòng bệnh;hiệu thuốc;thuốc;ống nghe;nhiệt độ;tiêm;truyền dịch;vết thương;co giật;bỏng;ung thư;tái phát;tỉnh táo;ngất;vi khuẩn;khẩu trang;cách ly;Cô vy (covid);sức khỏe;chăm sóc sức khỏe;vệ sinh cá nhân;cứu sống;cứu;cầu cứu;bảo hiểm;đăng ký;tiếp tân;châm cứu;chẩn đoán;khám;huyết áp;ho;đau đầu;dị ứng;chóng mặt;buồn nôn;khát nước;thở;thở dài;tiêu hoá;đánh răng;súc miệng;còi xương;tím tái;xanh xao;ốm đau;bệnh thủy đậu;chất độc;độc hại;đề phòng;tác dụng;không;chưa',
'Cơ thể': 'bụng;cơ thể;cơ bắp;bàn tay;bàn chân;cánh tay;đôi tay;đôi chân;chân tay;cổ;cổ họng;cổ tay;cổ chân;cùi chỏ;đầu gối;cột sống;tuỷ sống;thần kinh;tim;thận;phổi;gan;dạ dày;ruột;máu;mạch máu;răng;lưỡi;môi;miệng;mắt;tai;mũi;đầu;tóc;vai;ngực;lưng;da;buồng trứng;tinh trùng;thị giác;thị lực;cử động;chớp mắt;giơ tay;nhắm mắt;há miệng;ấn;béo;cân nặng;chiều cao',
'Giao tiếp': 'bạn;ai;chào;tạm biệt;trả lời;trả (đt);bao nhiêu?;vì sao?;thế nào?;bao giờ?;tên là gì?;địa chỉ;địa điểm;chỉ dẫn;yêu cầu;đề nghị;đồng ý;tán thành;từ chối;không cần;cần không?;có … không?;đúng không?;còn bạn?;cũng vậy/cũng thế;chúng tôi (đại từ);các bạn;bản thân;tự (tự làm);chọn lựa;chọn lọc;giải thích;hiểu;không hiểu;nhắc lại;thắc mắc;giới thiệu;đối thoại;chuyện trò;lắng nghe;tập trung;tôn trọng;tin cậy;yên tâm;yên lòng;yên bình;bình thường;chính xác;đơn giản;vấn đề;cụ thể;trực tiếp;tiếp nhận;tiếp theo;thực hiện;chuẩn bị;bắt đầu;kết thúc;chấm dứt;thống nhất;hợp tác;chia sẻ;bảo đảm;giữ gìn;bỏ qua;thông báo;tin nhắn;tiếng nói;âm thanh;ngôn ngữ ký hiệu;người Điếc;người lớn;người già;trẻ con/con nít',
'Thời gian': 'ban ngày;ban đêm;buổi đêm;chiều tối;cả ngày;tuần;tuần này;tuần sau;tuần trước;cuối tuần;cuối tháng;cuối năm;năm nay;năm sau;năm trước;hôm nay;hôm qua;ngày mai;sáng mai;hàng ngày;thời gian biểu;đều đặn;lúc;trước;sau;đầu tiên;thứ tự;trong khoảng;hiện tại;tương lai;quá khứ;đồng hồ;đếm;1;2;3;4;5;6;7;8;9;10;11;12;100;1000 (một nghìn);0 (số không)',
'Sinh hoạt': 'ăn uống;đồ ăn;đồ uống;thực phẩm;bữa cơm;ăn đủ;ăn ít;ăn vừa;ăn vặt;đói không?;nhai;nuốt;no;đói;đi vệ sinh;toa lét;bệ xí;cuộn giấy vệ sinh;bàn chải đánh răng;chai nước;bình sữa (em bé);xà phòng;xà phòng giặt;rửa mặt;đánh răng;súc miệng;cởi áo;mặc áo;áo;áo ấm;áo phông;áo len;quần;quần áo;khăn;khăn mặt;găng tay;bao tay (dùng cho trẻ sơ sinh);bít tất;đôi dép;giày dép;cái túi;va li;cúc áo;chăn (cái chăn);chiếc gối;đệm;ghế;bàn ghế;bát;chén;đĩa;đũa;cốc;tách;thìa;ấm đun nước;nồi;chảo;dao;chìa khóa;cửa sổ;cửa kính;đóng cửa;mở cửa;bật đèn;đèn điện;đèn pin;cầu thang;thẻ;vé;danh sách;tờ giấy;bút;bút bi;bút máy;chữ viết;đọc sách;đeo kính;điều hòa;vòi nước;ổn định;ưu tiên;xếp hàng;xếp hàng ưu tiên',
'Ăn uống': 'cơm hộp;cơm bình dân;cơm rang;gạo;bánh mì;bánh cuốn;bánh giò;bánh chưng;bánh tét;bánh bột lọc;bánh xèo;bún;phở;cháo;cháo sườn;miến;mì;trứng;thịt;thịt bò;thịt gà;thịt lợn;cá kho;con cá;con tôm;con cua;con mực;con ghẹ;con hàu;con sò;rau;rau xanh;muối;đường;sữa;trà;trà nóng;trà đá;trà sữa;cà phê;nước lọc;nước cam;nước dừa;chanh nóng;chanh muối;chanh đá;ấm trà;đông lạnh;nóng;lạnh;ngọt;mặn;chua;cay;đắng;nhạt;thơm;thối;chiên/rán (1)(2);luộc;nấu;nướng;xào;hấp;chín;sống;quả cam;quả chuối;quả xoài;quả dừa;quả bơ;quả táo;quả lê;quả ổi;quả đu đủ;quả dứa;quả dâu;quả nho;quả đào;quả mận;quả vải;củ khoai lang;củ khoai tây;củ cà rốt;củ cải trắng;củ hành tây;củ gừng;củ nghệ;củ tỏi;bắp ngô;bia;rượu;thuốc lá',
'Gia đình': 'bố;mẹ;cha;cha mẹ;bố mẹ;ông bà;ông ngoại;ông nội;bà ngoại;bà nội;ông già;cụ già;cụ;anh ruột;anh hai, anh cả;chị hai, chị cả;chị;em;em trai;em gái;anh em;anh chị em;con gái;con trai;con nuôi;con đẻ;cháu gái;cháu trai;cháu nội;cháu ngoại;chú ( người);dì;cô;chồng;vợ;bạn gái;bạn trai;người thân;họ hàng;gia đình;người bảo trợ;phụ huynh',
'Hoạt động': 'đi dạo;di chuyển;đi;vào;xuống;lên;cúi;ngồi;nằm;đứng;đứng nghiêm;đẩy;kéo;đặt;để (đặt);giữ;cầm;nắm;bắt;chạm;va chạm;cử động;vận động;tập thể dục;thể dục;bước;bước chân;chạy chậm;chạy nhanh;chạy;quay;uốn;uốn cong;nâng;hạ;co dãn;bế em;cõng;ôm;bắt tay;vỗ tay;vẫy tay;vỗ về;trông coi;trông nom;học;học sinh;giáo viên;thầy cô;cô giáo;công việc;việc làm;làm việc;giúp;hỗ trợ;thử;tìm hiểu;tìm;quan sát;xem xét;chụp ảnh;viết;đọc;vẽ;tập viết;báo cáo;sử dụng;công cụ;dụng cụ;chức năng;đổi;chuyển đồ;vận chuyển;cất giữ;gửi;nhận;cho;trả lời;bảo vệ;chờ đợi;tiếp tục;tuân thủ;tuân lệnh',
'Cảm xúc': 'vui mừng;vui sướng;vui tính;tươi cười;lo lắng;lo sợ;sợ hãi;buồn;buồn thảm;khóc;cười;đau;khỏe;mệt;yếu;mạnh;nhẹ;nặng;nóng;lạnh;ấm áp;bình an;bối rối;thắc mắc;thất vọng;hy vọng;tự tin;tự lập;hài lòng;hạnh phúc;cô đơn;cực khổ;vội vã;chậm chạp;thật thà;tức giận;bực mình;ức chế;ân hận;tò mò;tích cực;tiêu cực;tuyệt vọng;động viên;cố gắng;kiên nhẫn;bình tĩnh;thân thiện;dũng cảm;yêu mến (yêu quí);yêu thương;ghét;thích;muốn;cần;hứa;hứa hẹn',
'Không gian': 'bên cạnh;bên dưới;bên trong;bên trên;bên phải;bên trái;đằng trước;đằng sau;ở ngoài;ở trong;đối diện;gần;xa;trước;sau;trung tâm;cổng;cửa hàng;nhà hàng;siêu thị;ngân hàng;công viên;nhà trọ;trường tiểu học;xe máy;xe đạp;ô tô;xe khách;xe tải;xe buýt;trạm xe buýt;bến xe;đi lạc (đường, rừng..);xe cứu thương;địa chỉ;địa điểm;đường bộ;đèn báo giao thông;đèn xanh;đèn đỏ;đèn vàng;bảng chỉ dẫn;phòng;trong ngoài;vị trí;nhà;bệnh viện;hiệu thuốc;trạm y tế;quán cà phê;thành phố;Việt Nam',
}

def key(s):return ' '.join(unicodedata.normalize('NFC',s).casefold().strip().rstrip('?!.').split())

def main():
    index=json.loads((ROOT/'research/qipedc-dictionary-index.json').read_text('utf8'))
    words=json.loads((ROOT/'assets/vocabulary.json').read_text('utf8'));existing={key(w['label']) for w in words}
    source={}
    for row in index['entries']:source.setdefault(key(row['word']),[]).append(row)
    desired={}
    for group,terms in GROUPS.items():
        for term in terms.split(';'):desired.setdefault(key(term),(term,group))
    # Extend with the original everyday vocabulary after the clinical terms.
    for row in json.loads((ROOT/'assets/catalog.json').read_text('utf8'))['words']:
        desired.setdefault(key(row['label']),(row['label'],'Sinh hoạt'))
    candidates=[];missing=[]
    for k,(term,group) in desired.items():
        if k in existing:continue
        if k not in source:missing.append(term);continue
        options=sorted(source[k],key=lambda r:(0 if r['source_id'].endswith('N') else 1 if not r['source_id'][-1].isalpha() else 2,r['source_id']))
        chosen=options[0]
        candidates.append({'id':'qipedc-'+chosen['source_id'],'label':chosen['word'][:1].upper()+chosen['word'][1:],'category':group,'description':chosen['description'],'source_id':chosen['source_id'],'url':chosen['video_url'],'alternatives':[r['source_id'] for r in options[1:]],'regional_status':'Filename preference only; no verified regional assignment.','status':'awaiting-source-and-visual-review'})
    target=200; candidates=candidates[:max(0,target-len(words))]
    out={'schema':'clinic-dictionary-expansion-plan-v1','target_total':target,'existing_motion_words':len(words),'candidate_count':len(candidates),'planned_total':len(words)+len(candidates),'method':'Editorial task coverage; not measured word frequency. Prefer N suffix where available, otherwise unsuffixed; verify source signing before import.','index_source':index['source'],'new_motion_words_accepted':0,'source_access':'2026-11-15: direct HTTP/HTTPS and Chrome ERR_CONNECTION_RESET; cached official index only.','candidates':candidates,'unmatched_requested_terms':missing}
    (ROOT/'research/dictionary-expansion-plan.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({k:v for k,v in out.items() if k not in ['index_source','candidates','unmatched_requested_terms']},ensure_ascii=False))
    print('unmatched:',len(missing))

if __name__=='__main__':main()
