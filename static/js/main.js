/* VoltTrack Battery Shop JavaScript Functions */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alert toasts after 4 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 4000);
    });
});

// Calculate billing totals in create_bill.html
function updateBillingCalculations() {
    const rows = document.querySelectorAll('.bill-item-row');
    let subtotal = 0;

    rows.forEach((row, index) => {
        const select = row.querySelector('.product-select');
        const qtyInput = row.querySelector('.qty-input');
        const priceInput = row.querySelector('.price-input');
        const totalSpan = row.querySelector('.item-total');

        if (select && select.value) {
            const opt = select.options[select.selectedIndex];
            const defaultPrice = parseFloat(opt.dataset.price || 0);
            
            if (!priceInput.value || priceInput.dataset.manual !== 'true') {
                priceInput.value = defaultPrice;
            }

            const qty = parseInt(qtyInput.value) || 1;
            const unitPrice = parseFloat(priceInput.value) || 0;
            const lineTotal = qty * unitPrice;

            totalSpan.textContent = '₹' + lineTotal.toLocaleString('en-IN', {minimumFractionDigits: 2});
            subtotal += lineTotal;

            // Generate Serial Number Inputs
            renderSerialInputs(row, index, qty, opt.dataset.brand);
        }
    });

    const gstRate = parseFloat(document.getElementById('gst_rate')?.value || 18);
    const oldRebate = parseFloat(document.getElementById('old_battery_rebate')?.value || 0);

    const gstAmount = subtotal * (gst_rate / 100);
    const grandTotal = Math.max(0, (subtotal + gstAmount) - oldRebate);

    if (document.getElementById('subtotal_display')) {
        document.getElementById('subtotal_display').textContent = '₹' + subtotal.toLocaleString('en-IN', {minimumFractionDigits: 2});
    }
    if (document.getElementById('gst_amount_display')) {
        document.getElementById('gst_amount_display').textContent = '₹' + gstAmount.toLocaleString('en-IN', {minimumFractionDigits: 2});
    }
    if (document.getElementById('grand_total_display')) {
        document.getElementById('grand_total_display').textContent = '₹' + grandTotal.toLocaleString('en-IN', {minimumFractionDigits: 2});
    }
}

// Dynamically create serial number input fields per quantity
function renderSerialInputs(row, rowIndex, qty, brand) {
    const container = row.querySelector('.serials-container');
    if (!container) return;

    let existingInputs = container.querySelectorAll('input');
    let currentValues = [];
    existingInputs.forEach(i => currentValues.push(i.value));

    container.innerHTML = '';
    const label = document.createElement('div');
    label.className = 'text-muted small mb-1 font-weight-bold';
    label.innerHTML = `<i class="fas fa-barcode text-warning"></i> Battery Serial No(s) for Warranty:`;
    container.appendChild(label);

    const flexDiv = document.createElement('div');
    flexDiv.className = 'd-flex flex-wrap gap-2';

    const brandPrefix = (brand || 'VOLT').substring(0, 3).toUpperCase();
    const currentYear = new Date().getFullYear();

    for (let i = 0; i < qty; i++) {
        const input = document.createElement('input');
        input.type = 'text';
        input.name = `serials_${rowIndex}[]`;
        input.className = 'form-control form-control-sm border-warning';
        input.style.maxWidth = '200px';
        input.placeholder = `Serial #${i + 1}`;
        
        // Preserve existing value or generate placeholder format
        if (currentValues[i]) {
            input.value = currentValues[i];
        } else {
            const randomNum = Math.floor(10000 + Math.random() * 90000);
            input.value = `${brandPrefix}-${currentYear}-${randomNum}`;
        }

        flexDiv.appendChild(input);
    }
    container.appendChild(flexDiv);
}
