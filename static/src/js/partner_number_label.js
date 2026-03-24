/** @odoo-module **/

import { FormRenderer } from "@web/views/form/form_renderer";
import { patch } from "@web/core/utils/patch";

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        // Run once after mount + on record changes
        this.env.model.addEventListener("update", () => this._updateNumberLabel());
        this.onMounted(() => this._updateNumberLabel());
    },

    _updateNumberLabel() {
        const fieldEl = this.el.querySelector("field[name='vendor_number']");
        if (!fieldEl) return;

        // Find the label element (usually the previous sibling with class o_form_label)
        let labelEl = fieldEl.closest(".o_field_widget")?.previousElementSibling;
        if (!labelEl || !labelEl.classList.contains("o_form_label")) {
            // Fallback: find nearest label
            labelEl = fieldEl.closest("div").querySelector("label");
        }
        if (!labelEl) return;

        const data = this.props.record.data;
        const isVendor   = data.supplier_rank > 0;
        const isCustomer = data.customer_rank > 0;

        let newLabel = "Partner Number";
        if (isVendor && isCustomer) {
            newLabel = "Vendor / Customer Number";
        } else if (isVendor) {
            newLabel = "Vendor Number";
        } else if (isCustomer) {
            newLabel = "Customer Number";
        }

        // Add colon if you want (consistent with your original XML)
        labelEl.textContent = newLabel + ":";
    }
});