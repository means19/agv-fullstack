# Physics-Based AGV Energy Modeling (Mô hình năng lượng vật lý cho AGV)

## 1. Vai trò & Mục tiêu
- Vai trò: Expert Research Engineer in Cyber-Physical Systems (CPS) & AGV Dynamics.  
- Mục tiêu: Nâng cấp module tính năng lượng của mô phỏng AGV từ mô hình tuyến tính hệ số sang "Physics-based Kinetic Model" để đạt chuẩn khoa học (theo yêu cầu supervisor).

---

## 2. Bối cảnh & Tài liệu tham khảo
- Mô hình hiện tại: E = C × d (tuyến tính).  
- Yêu cầu: Tuân theo phương trình động lực trong: "Energy and Time-Efficient Scheduling of Automated Guided Vehicles System" (Section II.B, Equations 2–10).  
- Đơn vị chuẩn: SI (kg, m, s, J). Kết quả trả về: kJ.

---

## 3. Nguyên lý vật lý cốt lõi

- Công suất tiêu thụ:
    $$P_e = \frac{P_{motion}}{\eta} + P_{idle}$$
    với η = hiệu suất động cơ, P_idle = công suất phụ trợ (CPU, sensors).

- Công suất chuyển động:
    $$P_{motion} = (F_{friction} + F_{inertia}) \times v$$

- Lực:
    - Ma sát lăn:
        $$F_{fr} = (m_{AGV} + m_{load}) \cdot g \cdot \mu_r$$
    - Quán tính (gia tốc):
        $$F_{in} = (m_{AGV} + m_{load}) \cdot a$$

---

## 4. Yêu cầu triển khai (tóm tắt kỹ thuật)

4.1 Motion profiling (Kinematics)
- Sử dụng Trapezoidal Velocity Profile với ba pha:
    1. Acceleration: vượt qua lực ma sát + quán tính.  
    2. Cruising: duy trì vận tốc tối đa, chỉ khắc phục ma sát.  
    3. Deceleration: giảm tốc; coi lực ma sát hỗ trợ phanh (ít/không tiêu tốn động cơ).
- Edge case: Nếu quãng đường quá ngắn để đạt vmax → Triangular Profile.

4.2 Cấu hình (config.py)
- Thay hệ số đơn bằng hằng số vật lý trong dataclass `EnergyConfig`:
    - mass_agv (kg): ~30–50
    - friction_coeff μ: ~0.02–0.03
    - gravity g: 9.81 m/s²
    - motor_efficiency η: ~0.6–0.8
    - max_velocity vmax: ~1.0 m/s
    - acceleration a: ~0.5–1.5 m/s²
    - idle_power P_idle (W) — công suất phụ trợ cần được khai báo

4.3 Logic tính toán (energy_calculation.py)
- Hàm `calculate_travel_energy(distance_m, load_mass, config)` phải:
    1. Kiểm tra tính hợp lệ đầu vào (distance ≥ 0, khối lượng ≥ 0, cấu hình hợp lệ).
    2. Xác định profile: Trapezoidal hoặc Triangular dựa trên distance và các thông số (vmax, a).
    3. Tính công cơ học (Work) của từng pha:
         - Acceleration: tích phân lực × quãng đường (hoặc dùng công ΔK = 0.5·m·(v_f^2−v_i^2) cộng công ma sát trên đoạn đó).
         - Cruising: công bù ma sát = F_fr · d_cruise.
         - Deceleration: coi phần năng lượng hãm không trả lại (kinetic dissipated) — nếu regenerative ≈ 0 thì bỏ qua chuyển năng; nếu không có mô tả regen, xem là tiêu cực/không sinh công điện.
    4. Chuyển công cơ học sang năng lượng điện: E_electric_motion = W_mechanical / η.
    5. Cộng năng lượng idle: E_idle = P_idle · total_time.
    6. Trả về tổng năng lượng tính bằng Kilojoule (kJ). Nếu distance == 0 → trả 0 kJ.

---

## 5. Yêu cầu kỹ thuật bổ sung
- Giữ cấu trúc class `EnergyCalculationService` để tương thích ngược.  
- Strict type hinting cho Python.  
- Tất cả tính toán nội bộ ở SI; chuyển kết quả cuối sang kJ (1 kJ = 1000 J).  
- Xử lý góc cạnh (zero-distance, very-short distance → triangular).  
- Kiểm soát đơn vị và kiểm tra giá trị vượt ngưỡng (ví dụ: v_max ≤ 0, a ≤ 0 → lỗi).

---

## 6. Deliverables (tổng kết)
1. Updated `config.py`: dataclass `EnergyConfig` chứa các tham số vật lý.  
2. Updated `energy_calculation.py`: hàm `calculate_travel_energy` theo logic vật lý nêu trên, trả về kJ.  
3. Scientific justification ngắn (dưới): dùng để biện hộ trước supervisor.

---

## 7. Scientific justification (tóm tắt)
- Mô hình vật lý tách bạch các thành tố tiêu thụ (ma sát, quán tính, phụ trợ) phản ánh phi tuyến, phụ thuộc tải và hồ sơ chuyển động — khác biệt cơ bản so với E = C·d.  
- Khi tải thay đổi hoặc đoạn ngắn/ dài khác nhau, phân bố năng lượng giữa pha tăng tốc/cruise/giảm tốc biến đổi rõ rệt; mô hình vật lý bắt được ảnh hưởng này.  
- Phân chia công cơ và hệ số hiệu suất (η) cho phép tách rò rỉ/hiệu quả truyền động, hỗ trợ đánh giá cải tiến phần cứng (motor, regenerative braking) một cách có cơ sở.

---

## 8. Gợi ý kiểm thử (ngắn)
- Trường hợp cơ bản: distance = 0 → 0 kJ.  
- Trường hợp triangular: distance nhỏ hơn d_min để đạt vmax → so sánh năng lượng bằng cách tính ΔK + ma sát.  
- So sánh với model tuyến tính để minh họa khác biệt (khối lượng tăng → năng lượng tăng không tỉ lệ tuyến tính).

--- 

Tài liệu này đủ để chuyển thành mã trong hai file đã nêu mà không làm thay đổi cấu trúc lớp hiện tại; các công thức và ràng buộc đã được chỉ rõ để hiện thực hóa mô hình energy-based cho AGV.
