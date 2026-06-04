@receipt_bp.route('/process/<int:receipt_id>', methods=['POST'])
def process_receipt(receipt_id):
    result = receipt_service.process_receipt(receipt_id)
    return jsonify(result)