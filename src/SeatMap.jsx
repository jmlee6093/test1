const ROW_LABELS   = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
const SEAT_NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

const styles = {

  background: {
    width: "100%",
    height: "100%",
    background: "#1a1a2e",
    borderRadius: "12px",
    boxSizing: "border-box",
    padding: "12px 16px 12px 0",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-around",
  },

  row: {
    display: "flex",
    alignItems: "center",
    gap: "5px",
    flex: 1,                   
    maxHeight: "36px",
  },

  rowLabel: {
    width: "32px",            
    textAlign: "center",
    fontSize: "11px",
    fontWeight: 500,
    color: "#5a6480",
    flexShrink: 0,
  },

  seatGroup: {
    display: "flex",
    gap: "5px",
    flex: 1,       
    height: "100%",       
  },

  seat: {
    flex: 1,                   
    height: "100%",
    background: "#A20812",
    borderRadius: "3px 3px 5px 5px",
    borderTop: "2px solid #D81B26",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "7px",
    color: "#a8d4f5",
    minWidth: 0,               
  },

};

export default function SeatMap() {
  return (
    <div style={styles.background}>
      {ROW_LABELS.map((label) => (
        <div key={label} style={styles.row}>

          <span style={styles.rowLabel}>{label}</span>

          <div style={styles.seatGroup}>
            {SEAT_NUMBERS.map((num) => (
              <div key={num} style={styles.seat}>
                {num}
              </div>
            ))}
          </div>

        </div>
      ))}
    </div>
  );
}