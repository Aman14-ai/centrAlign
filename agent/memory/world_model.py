from typing import Optional
from pydantic import BaseModel, Field

from agent.memory.entities import (
    Vendor, PurchaseOrder, Invoice, Employee, ExpenseReport, FileFacts,
)


class WorldModel(BaseModel):
    # Entities
    vendors: dict[str, Vendor] = Field(default_factory=dict)
    purchase_orders: dict[str, PurchaseOrder] = Field(default_factory=dict)
    invoices: dict[str, Invoice] = Field(default_factory=dict)
    employees: dict[str, Employee] = Field(default_factory=dict)
    expense_reports: dict[str, ExpenseReport] = Field(default_factory=dict)
    files: dict[str, FileFacts] = Field(default_factory=dict)

    # Meta
    facts: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    scratchpad: list[str] = Field(default_factory=list)

    # ---- Upserts ----

    def add_vendor(self, vendor: Vendor) -> None:
        self.vendors[vendor.id] = vendor

    def add_po(self, po: PurchaseOrder) -> None:
        self.purchase_orders[po.po_number] = po

    def add_invoice(self, invoice: Invoice) -> None:
        self.invoices[invoice.id] = invoice

    def add_employee(self, employee: Employee) -> None:
        self.employees[employee.id] = employee

    def add_expense(self, expense: ExpenseReport) -> None:
        self.expense_reports[expense.id] = expense

    def add_file_facts(self, facts: FileFacts) -> None:
        self.files[facts.path] = facts

    # ---- Lookups ----

    def find_vendor_by_name(self, name: str) -> list[Vendor]:
        return [v for v in self.vendors.values() if v.matches_name(name)]

    def find_invoice(self, invoice_id: str) -> Optional[Invoice]:
        return self.invoices.get(invoice_id)

    def find_po(self, po_number: str) -> Optional[PurchaseOrder]:
        return self.purchase_orders.get(po_number)

    # ---- Meta mutations ----

    def add_fact(self, fact: str) -> None:
        if fact and fact not in self.facts:
            self.facts.append(fact)

    def add_uncertainty(self, note: str) -> None:
        if note and note not in self.uncertainties:
            self.uncertainties.append(note)

    def clear_uncertainty(self, note: str) -> None:
        if note in self.uncertainties:
            self.uncertainties.remove(note)

    def add_scratch(self, note: str, max_entries: int = 20) -> None:
        if note:
            self.scratchpad.append(note)
            if len(self.scratchpad) > max_entries:
                self.scratchpad = self.scratchpad[-max_entries:]

    # ---- Serialization for LLM prompt ----

    def to_prompt_text(self, max_facts: int = 20, max_scratch: int = 10) -> str:
        """Format world knowledge for the planner's prompt."""
        lines: list[str] = []

        if self.vendors:
            lines.append("Vendors:")
            for v in self.vendors.values():
                aliases = f" (aliases: {', '.join(v.aliases)})" if v.aliases else ""
                email = f" | email: {v.email}" if v.email else ""
                lines.append(f"  {v.id}: {v.name}{aliases}{email}")

        if self.purchase_orders:
            lines.append("Purchase Orders:")
            for p in self.purchase_orders.values():
                lines.append(f"  {p.po_number}: vendor={p.vendor_id}, amount={p.amount}")

        if self.invoices:
            lines.append("Invoices:")
            for i in self.invoices.values():
                lines.append(
                    f"  {i.id}: vendor={i.vendor_id}, amount={i.amount}, "
                    f"due={i.due_date}, po={i.po_number}"
                )

        if self.employees:
            lines.append("Employees:")
            for e in self.employees.values():
                lines.append(f"  {e.id}: {e.name} ({e.department})")

        if self.expense_reports:
            lines.append("Expense Reports:")
            for x in self.expense_reports.values():
                lines.append(
                    f"  {x.id}: employee={x.employee_id}, amount={x.amount}, "
                    f"category={x.category}, status={x.status}"
                )

        if self.files:
            lines.append("Files read:")
            for f in self.files.values():
                lines.append(
                    f"  {f.path}: vendor={f.vendor}, invoice={f.invoice_number}, "
                    f"amount={f.amount}, due={f.due_date}, po={f.po_number}"
                )

        if self.facts:
            lines.append("Facts:")
            for fact in self.facts[-max_facts:]:
                lines.append(f"  - {fact}")

        if self.uncertainties:
            lines.append("Uncertainties:")
            for u in self.uncertainties:
                lines.append(f"  ? {u}")

        if self.scratchpad:
            lines.append("Scratchpad:")
            for s in self.scratchpad[-max_scratch:]:
                lines.append(f"  ~ {s}")

        return "\n".join(lines) if lines else "(no world knowledge yet)"