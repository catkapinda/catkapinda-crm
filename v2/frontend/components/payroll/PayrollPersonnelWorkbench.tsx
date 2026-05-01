"use client";

import { useMemo, useState } from "react";
import {
  Search,
  Download,
  X,
  ChevronRight,
  FileText,
  Wallet,
  CircleMinus,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import styles from "./PayrollPersonnelWorkbench.module.css";

type DeductionItem = {
  label: string;
  amount: number | null;
};

type PayrollWorkbenchPerson = {
  id: number;
  name: string;
  role: string;
  status: string;
  netPayment: number | null;
  earning: number | null;
  deduction: number | null;
  withholding: number | null;
  model: string;
  deductions?: DeductionItem[];
};

type PayrollPersonnelWorkbenchProps = {
  people?: PayrollWorkbenchPerson[];
  onDownloadPdf?: (person: PayrollWorkbenchPerson) => void | Promise<void>;
};

const formatMoney = (value: number | null | undefined | string) => {
  if (value === null || value === undefined || value === "") return "—";
  return (
    new Intl.NumberFormat("tr-TR", {
      maximumFractionDigits: 0,
    }).format(Number(value)) + " ₺"
  );
};

const getInitials = (name = "") =>
  name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((x) => x[0])
    .join("")
    .toUpperCase();

export default function PayrollPersonnelWorkbench({
  people = [],
  onDownloadPdf,
}: PayrollPersonnelWorkbenchProps) {
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("all");
  const [sort, setSort] = useState("net_desc");

  const filteredPeople = useMemo(() => {
    let result = [...people];

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((p) =>
        `${p.name || ""} ${p.role || ""} ${p.model || ""}`
          .toLowerCase()
          .includes(q),
      );
    }

    if (role !== "all") {
      result = result.filter((p) => p.role === role);
    }

    result.sort((a, b) => {
      if (sort === "net_desc") return (b.netPayment || 0) - (a.netPayment || 0);
      if (sort === "earning_desc") return (b.earning || 0) - (a.earning || 0);
      if (sort === "deduction_desc") return (b.deduction || 0) - (a.deduction || 0);
      return 0;
    });

    return result;
  }, [people, role, search, sort]);

  const selectedPerson = useMemo(() => {
    if (!selectedPersonId) return null;
    return people.find((p) => p.id === selectedPersonId) || null;
  }, [people, selectedPersonId]);

  const roles = useMemo(() => {
    return Array.from(new Set(people.map((p) => p.role).filter(Boolean)));
  }, [people]);

  const cx = (...names: Array<string | false | null | undefined>) =>
    names.filter(Boolean).map((name) => styles[name as string]).join(" ");

  return (
    <section className={styles["ck-pl-workbench"]}>
      <div className={styles["ck-pl-list-card"]}>
        <div className={styles["ck-pl-list-head"]}>
          <div>
            <h2>Personel Listesi</h2>
            <p>Seçili dönemdeki hakediş kayıtlarını inceleyin.</p>
          </div>
          <span className={styles["ck-pl-count"]}>{filteredPeople.length} kişi</span>
        </div>

        <div className={styles["ck-pl-filters"]}>
          <div className={styles["ck-pl-search"]}>
            <Search size={18} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Personel ara..."
            />
          </div>

          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="all">Tüm roller</option>
            {roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>

          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="net_desc">Net ödeme</option>
            <option value="earning_desc">Hakediş</option>
            <option value="deduction_desc">Kesinti</option>
          </select>
        </div>

        <div className={styles["ck-pl-list"]}>
          {filteredPeople.map((person) => {
            const selected = selectedPersonId === person.id;

            return (
              <button
                key={person.id}
                className={cx("ck-pl-row", selected && "is-selected")}
                onClick={() => setSelectedPersonId(person.id)}
                type="button"
              >
                <div className={styles["ck-pl-avatar"]}>{getInitials(person.name)}</div>

                <div className={styles["ck-pl-person"]}>
                  <strong>{person.name || "—"}</strong>
                  <span>
                    {person.role || "—"} • {person.model || "Model yok"}
                  </span>
                </div>

                <span
                  className={cx(
                    "ck-pl-status",
                    person.status === "Aktif" && "is-active",
                  )}
                >
                  {person.status || "—"}
                </span>

                <div className={styles["ck-pl-money-block"]}>
                  <small>Net Ödeme</small>
                  <strong>{formatMoney(person.netPayment)}</strong>
                </div>

                <ChevronRight size={18} className={styles["ck-pl-chevron"]} />
              </button>
            );
          })}
        </div>
      </div>

      <aside className={styles["ck-pl-detail-card"]}>
        {!selectedPerson ? (
          <div className={styles["ck-pl-empty"]}>
            <div className={styles["ck-pl-empty-icon"]}>
              <UserRound size={28} />
            </div>
            <h3>Personel seçin</h3>
            <p>Detayları görmek için soldaki listeden bir personel seçin.</p>
          </div>
        ) : (
          <>
            <div className={styles["ck-pl-detail-top"]}>
              <div className={cx("ck-pl-avatar", "large")}>
                {getInitials(selectedPerson.name)}
              </div>

              <div className={styles["ck-pl-detail-title"]}>
                <h3>{selectedPerson.name}</h3>
                <p>{selectedPerson.role}</p>
              </div>

              <button
                className={styles["ck-pl-clear"]}
                onClick={() => setSelectedPersonId(null)}
                aria-label="Seçimi temizle"
                type="button"
              >
                <X size={18} />
              </button>
            </div>

            <span className={cx("ck-pl-status", "is-active")}>
              {selectedPerson.status || "Aktif"}
            </span>

            <div className={styles["ck-pl-tabs"]}>
              <button className={styles["is-active"]} type="button">
                Finans Özeti
              </button>
              <button type="button">Operasyon</button>
              <button type="button">Trend</button>
              <button type="button">PDF</button>
            </div>

            <div className={styles["ck-pl-metrics"]}>
              <Metric
                icon={<Wallet size={18} />}
                label="Net Ödeme"
                value={formatMoney(selectedPerson.netPayment)}
              />
              <Metric
                icon={<FileText size={18} />}
                label="Hakediş"
                value={formatMoney(selectedPerson.earning)}
              />
              <Metric
                icon={<CircleMinus size={18} />}
                label="Kesinti"
                value={formatMoney(selectedPerson.deduction)}
              />
              <Metric
                icon={<ShieldCheck size={18} />}
                label="Tevkifat"
                value={formatMoney(selectedPerson.withholding)}
              />
            </div>

            <div className={styles["ck-pl-section"]}>
              <div className={styles["ck-pl-section-title"]}>
                <h4>Kesinti Kalemleri</h4>
              </div>

              <div className={styles["ck-pl-deductions"]}>
                {(selectedPerson.deductions || []).length ? (
                  selectedPerson.deductions?.map((item, index) => (
                    <div className={styles["ck-pl-deduction-row"]} key={index}>
                      <span title={item.label}>{item.label}</span>
                      <strong>{formatMoney(item.amount)}</strong>
                    </div>
                  ))
                ) : (
                  <p className={styles["ck-pl-muted"]}>Kesinti kaydı bulunamadı.</p>
                )}

                <div className={styles["ck-pl-deduction-total"]}>
                  <span>Toplam Kesinti</span>
                  <strong>{formatMoney(selectedPerson.deduction)}</strong>
                </div>
              </div>
            </div>

            <button
              className={styles["ck-pl-primary-btn"]}
              onClick={() => onDownloadPdf?.(selectedPerson)}
              type="button"
            >
              <Download size={18} />
              Hakediş PDF’i İndir
            </button>
          </>
        )}
      </aside>
    </section>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className={styles["ck-pl-metric"]}>
      <div className={styles["ck-pl-metric-icon"]}>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
