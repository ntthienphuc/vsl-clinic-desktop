"""Finite interview mappings and rehearsal cases; no patient labels are added."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    path = ROOT / 'assets/phrases.json'
    catalog = json.loads(path.read_text(encoding='utf-8'))
    definitions = [
        ('ask-feeling-open', 'Bạn cảm thấy thế nào?', ['Bạn cảm thấy thế nào', 'Bạn cảm thấy như thế nào?', 'Bạn thấy thế nào?'], ['85', 'qipedc-W03239N'], 'wh_question', 'Cảm thấy → thế nào. Hỏi mở; không suy đoán triệu chứng từ câu hỏi.'),
        ('ask-abdomen-time', 'Bạn đau bụng vào lúc nào?', ['Bạn đau bụng vào lúc nào', 'Bạn đau bụng lúc nào?', 'Bạn đau bụng khi nào?', 'Bạn đau bụng bao giờ?'], ['qipedc-W00362', '379', 'qipedc-W00145N'], 'wh_question', 'Bụng → đau → bao giờ. Hỏi thời điểm, không thay thế câu hỏi thời gian kéo dài hoặc thời điểm bắt đầu.'),
        ('ask-sleep-time', 'Bạn ngủ vào lúc nào?', ['Bạn ngủ vào lúc nào', 'Bạn ngủ lúc nào?', 'Bạn ngủ khi nào?', 'Bạn ngủ bao giờ?'], ['222', 'qipedc-W00145N'], 'wh_question', 'Ngủ → bao giờ. Không suy ra số giờ ngủ hay mất ngủ.'),
        ('ask-wake-time', 'Bạn thức dậy vào lúc nào?', ['Bạn thức dậy vào lúc nào', 'Bạn thức dậy lúc nào?', 'Bạn thức dậy khi nào?', 'Bạn thức dậy bao giờ?', 'Bản thức dậy vào lúc nào', 'Bản thức dậy vào lúc nào?'], ['324', 'qipedc-W00145N'], 'wh_question', 'Thức dậy → bao giờ. Giữ câu hỏi đầy đủ bằng chữ.'),
        ('ask-want-sleep', 'Bạn có muốn ngủ không?', ['Bạn có muốn ngủ không'], ['169', '222'], 'yes_no_question', 'Muốn → ngủ, cùng nét mặt hỏi. Không chuyển thành kết luận thiếu ngủ.'),
        ('ask-appetite', 'Bạn có ăn ngon miệng không?', ['Bạn có ăn ngon miệng không', 'Bạn ăn có ngon miệng không?', 'Bạn ăn ngon miệng không?'], ['378', '212'], 'yes_no_question', 'Ăn → ngon miệng, cùng nét mặt hỏi.'),
        ('ask-feel-weak', 'Bạn có cảm thấy yếu không?', ['Bạn có cảm thấy yếu không', 'Bạn cảm thấy yếu không?'], ['85', '371'], 'yes_no_question', 'Cảm thấy → yếu. Không đồng nhất yếu với một chẩn đoán.'),
    ]
    ids = {row[0] for row in definitions}
    catalog['entries'] = [e for e in catalog['entries'] if e['id'] not in ids]
    for identity, text, aliases, glosses, act, explanation in definitions:
        catalog['entries'].append(dict(id=identity, text=text, aliases=aliases, gloss_ids=glosses, act=act, nonmanual='question', explanation=explanation))
    save(path, catalog)

    def step(doctor, ids, meaning, purpose):
        return dict(doctor=doctor, patient_ids=ids, meaning=meaning, purpose=purpose)

    scenarios = [dict(
        id='01_Dau_bung_va_trieu_chung_kem_theo', title='Đau bụng và các triệu chứng kèm theo',
        context='Người bệnh trong tình huống giả định đau bụng vào buổi sáng, thấy mệt, lạnh và yếu; trả lời có khi được hỏi về sốt. Bác sĩ hỏi thêm và đo nhiệt độ, chưa kết luận nguyên nhân.',
        patient_summary='Đau, mệt; đau vào buổi sáng; có đau bụng, lạnh, yếu và tự nhận có sốt; cần giúp đỡ và nghỉ ngơi.',
        steps=[
            step('Bây giờ bác sĩ khám bệnh.', [395], 'Đồng ý.', 'Mở đầu cuộc trao đổi, xin sự hợp tác.'),
            step('Bạn cảm thấy thế nào?', [379,204], 'Đau, mệt.', 'Để người bệnh tự nêu cảm giác trước khi hỏi cụ thể.'),
            step('Bạn có đau bụng không?', [79], 'Có.', 'Làm rõ vị trí đau; câu trả lời Có được hiểu cùng câu hỏi ngay trước đó.'),
            step('Bạn đau bụng vào lúc nào?', [4], 'Buổi sáng.', 'Hỏi thời điểm đau; không suy thành đã đau bao nhiêu ngày.'),
            step('Bạn có lạnh không?', [166], 'Lạnh.', 'Hỏi thêm cảm giác đi kèm.'),
            step('Bạn có cảm thấy yếu không?', [371], 'Yếu.', 'Hỏi tình trạng hiện tại bằng một câu ngắn.'),
            step('Bạn có sốt không?', [79], 'Có.', 'Ghi nhận lời kể; chưa có số đo nhiệt độ hoặc kết luận chẩn đoán.'),
            step('Bác sĩ đo nhiệt độ.', [395], 'Đồng ý.', 'Thông báo thao tác kiểm tra tiếp theo.'),
            step('Bạn có cần giúp đỡ không?', [87,116], 'Cần giúp đỡ.', 'Hỏi nhu cầu hỗ trợ.'),
            step('Bạn muốn nghỉ ngơi không?', [87,210], 'Cần nghỉ ngơi.', 'Cho người bệnh nêu nhu cầu nghỉ.'),
            step('Ngồi nghỉ ngơi.', [86], 'Cảm ơn.', 'Khép lại đoạn demo; không kê thuốc hoặc tự suy ra bệnh.'),
        ]), dict(
        id='02_Met_moi_giac_ngu_va_an_uong', title='Mệt mỏi, giấc ngủ và ăn uống',
        context='Người bệnh trong tình huống giả định đang mệt, muốn ngủ. Người bệnh ngủ buổi tối, thức dậy buổi sáng, vẫn ăn ngon miệng, tự uống nước và không cần người hỗ trợ.',
        patient_summary='Mệt, muốn ngủ; ngủ buổi tối, dậy buổi sáng; ăn ngon miệng; không cần giúp đỡ; cần nước và nghỉ ngơi.',
        steps=[
            step('Bây giờ bác sĩ khám bệnh.', [395], 'Đồng ý.', 'Mở một phiên mới để tách hai bệnh cảnh giả định.'),
            step('Bạn cảm thấy thế nào?', [204], 'Mệt.', 'Hỏi mở về cảm giác hiện tại.'),
            step('Bạn ngủ vào lúc nào?', [6], 'Buổi tối.', 'Hỏi giờ giấc sinh hoạt; chưa suy ra đủ hay thiếu ngủ.'),
            step('Bạn thức dậy vào lúc nào?', [4], 'Buổi sáng.', 'Bổ sung mốc thời gian còn lại.'),
            step('Bạn có muốn ngủ không?', [169,222], 'Muốn ngủ.', 'Làm rõ nhu cầu hiện tại.'),
            step('Bạn có ăn ngon miệng không?', [212], 'Ngon miệng.', 'Hỏi thêm tình trạng ăn uống.'),
            step('Bạn có cần giúp đỡ không?', [150], 'Không cần.', 'Thể hiện được một câu trả lời phủ định bằng đúng lớp Không cần.'),
            step('Bạn muốn uống nước không?', [87,243], 'Cần nước.', 'Chuyển từ hỏi tình trạng sang nhu cầu cụ thể.'),
            step('Uống nước nhé.', [395], 'Đồng ý.', 'Xác nhận một hành động trong kịch bản giả định.'),
            step('Bạn muốn nghỉ ngơi không?', [204,87,210], 'Mệt. Cần nghỉ ngơi.', 'Trình diễn từ hiện và được đọc ngay, rồi gom thành lượt.'),
            step('Ngồi nghỉ ngơi.', [86], 'Cảm ơn.', 'Khép lại cuộc trao đổi.'),
        ]),
    ]
    scenarios[1]['steps'][6]['patient_reference_ids'] = {'150': '022152'}
    save(ROOT / 'demo/scenarios-v0.3.6.json', dict(schema='clinic-rehearsal-v1', scope='Two fictional interview rehearsals, not diagnostic protocols. Patient replies use only unchanged 400 classes. Fluent signer review and live-user validation remain pending.', scenarios=scenarios))


if __name__ == '__main__':
    main()
