import Sheet from "../components/Sheet.jsx";
import Icon from "../components/Icon.jsx";
import { useSheets } from "../lib/sheets.jsx";

/** Her sayfadan açılan "Ekle" menüsü. */
export default function AddMenu({ onClose }) {
  const { open, close } = useSheets();
  const go = (type, props) => {
    close();
    setTimeout(() => open(type, props), 0);
  };
  const choices = [
    { icon: "wallet", title: "Alım / satım işlemi", text: "Elindeki bir varlığa alış veya satış ekle.", act: () => go("txn", {}) },
    { icon: "layers", title: "Yeni varlık", text: "Hisse, fon, altın veya döviz tanımla ve ilk alışını gir.", act: () => go("txn", { startNew: true }) },
    { icon: "card", title: "Borç veya kredi", text: "Taksit planı otomatik oluşturulur.", act: () => go("debt", {}) },
  ];
  return (
    <Sheet title="Ne eklemek istiyorsun?" onClose={onClose}>
      <div className="choices">
        {choices.map((c) => (
          <button key={c.title} className="choice" onClick={c.act}>
            <span className="choice__icon">
              <Icon name={c.icon} size={22} />
            </span>
            <span className="choice__text">
              <strong>{c.title}</strong>
              <span>{c.text}</span>
            </span>
            <Icon name="chevron" size={18} className="choice__go" />
          </button>
        ))}
      </div>
    </Sheet>
  );
}
