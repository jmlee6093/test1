import SeatMap from "./SeatMap";
import SeatGrid from "./SeatGrid";

const containerStyle = {
  position: "relative",  
  width: "100%",
  height: "220px",
};

export default function SeatSelector({ onChange }) {
  return (
    <div style={containerStyle}>
      <SeatMap />
      <SeatGrid onChange={onChange} />
    </div>
  );
}