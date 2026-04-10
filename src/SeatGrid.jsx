import { useState } from "react";

const GRID_ROWS = 6;
const GRID_COLS = 6;

const styles = {

  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    boxSizing: "border-box",
    paddingTop:    "12px",
    paddingBottom: "12px",
    paddingLeft:   "32px",
    paddingRight:  "16px",
    display: "grid",
    gridTemplateColumns: `repeat(${GRID_COLS}, 1fr)`,
    gridTemplateRows:    `repeat(${GRID_ROWS}, 1fr)`,
    gap: "3px",
    borderRadius: "12px",
  },

  cellDefault: {
    borderRadius: "4px",
    background: "rgba(99, 179, 237, 0.25)", 
    border: "1px solid rgba(99, 179, 237, 0.4)",
    cursor: "pointer",
    transition: "background 0.15s, border 0.15s",
  },

  cellSelected: {
    borderRadius: "4px",
    background: "rgba(15, 30, 80, 0.85)",    
    border: "1px solid rgba(30, 60, 130, 0.9)",
    cursor: "pointer",
    transition: "background 0.15s, border 0.15s",
  },

};

function EmptyGrid() {
  const grid = [];
  for (let r = 0; r < GRID_ROWS; r++) {
    const row = [];
    for (let c = 0; c < GRID_COLS; c++) {
      row.push(false);
    }
    grid.push(row);
  }
  return grid;
}

function PreferredSeat(grid) {
  let minRow = GRID_ROWS;
  let maxRow = -1;
  let minCol = GRID_COLS;
  let maxCol = -1;
  let hasSelected = false;

  for (let r = 0; r < GRID_ROWS; r++) {
    for (let c = 0; c < GRID_COLS; c++) {
      if (grid[r][c] === true) {
        hasSelected = true;
        if (r < minRow) minRow = r;
        if (r > maxRow) maxRow = r;
        if (c < minCol) minCol = c;
        if (c > maxCol) maxCol = c;
      }
    }
  }

  if (!hasSelected) return null;

  return {
    x_start: minCol / GRID_COLS,
    x_end:   (maxCol + 1) / GRID_COLS,
    y_start: minRow / GRID_ROWS,
    y_end:   (maxRow + 1) / GRID_ROWS,
  };
}

export default function SeatGrid({ onChange }) {

  const [grid, setGrid] = useState(EmptyGrid());

  function toggleCell(r, c) {
    setGrid((prev) => {

      const next = EmptyGrid();

      if (prev[r][c] === true) {
        onChange(null);
      } else {
        next[r][c] = true;
        onChange(PreferredSeat(next));
      }

      return next;
    });
  }

  return (
    <div style={styles.overlay}>
      {grid.map((row, r) =>
        row.map((isSelected, c) => (
          <button
            key={`${r}-${c}`}
            onClick={() => toggleCell(r, c)}
            style={isSelected ? styles.cellSelected : styles.cellDefault}
          />
        ))
      )}
    </div>
  );
}