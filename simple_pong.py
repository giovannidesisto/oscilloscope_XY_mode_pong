import numpy as np
import sounddevice as sd
import time
import curses

# --- Config ---
samplerate = 48000   #  48k
frame_time =  0.05 #   0.05  # 20 Hz
# gain = 1.0

# Campo di gioco 
scale = 1.0
field_left, field_right = -1.0*scale, 1.0*scale
field_bottom, field_top = -1.0*scale, 1.0*scale
margin = 0.2 * scale

# Paddle
paddle_w = 0.5
paddle_h = 0.1
player_x = 0.0
player_y = field_bottom + margin + paddle_h
cpu_x = 0.0
cpu_y = field_top - margin - paddle_h

# Palla quadrata
ball_size = paddle_w / 5
ball_dx_init = 0.05
ball_dy_init = 0.03
ball_on_paddle = True
ball_x = player_x
ball_y = player_y + paddle_h + ball_size/2
ball_dx = ball_dx_init
ball_dy = ball_dy_init
square_points_per_side = 100

# Numero punti per paddle e campo
paddle_points = 200
field_points = 400

# --- Audio callback ---
xy_points = np.zeros((1,2), dtype=np.float32)
def make_xy_stream(paths, frames):
    combined = np.vstack(paths)
    n = combined.shape[0]
    x = np.arange(n)
    xi = np.linspace(0, n-1, frames)
    x_interp = np.interp(xi, x, combined[:,0])
    y_interp = np.interp(xi, x, combined[:,1])
    return np.column_stack([x_interp, y_interp])

def callback(outdata, frames, time, status):
    global xy_points
    if xy_points.shape[0] != frames:
        xy_points = make_xy_stream([xy_points], frames)
    outdata[:] = xy_points.astype(np.float32)

# --- Loop principale ---
def main(stdscr):
    global player_x, cpu_x, ball_x, ball_y, ball_dx, ball_dy, xy_points, ball_on_paddle

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    with sd.OutputStream(channels=2, samplerate=samplerate, callback=callback):
        try:
            while True:
                # --- Input utente ---
                key = stdscr.getch()
                if key == curses.KEY_LEFT:
                    player_x -= 0.05
                elif key == curses.KEY_RIGHT:
                    player_x += 0.05
                elif key == curses.KEY_UP and ball_on_paddle:
                    ball_on_paddle = False

                player_x = np.clip(player_x, field_left + margin + paddle_w/2, field_right - margin - paddle_w/2)

                # --- CPU semplice ---
                if cpu_x < ball_x:
                    cpu_x += 0.04
                elif cpu_x > ball_x:
                    cpu_x -= 0.04
                cpu_x = np.clip(cpu_x, field_left + margin + paddle_w/2, field_right - margin - paddle_w/2)

                # --- Movimento palla ---
                if ball_on_paddle:
                    ball_x = player_x
                    ball_y = player_y + paddle_h + ball_size/2
                else:
                    ball_x += ball_dx
                    ball_y += ball_dy

                    # Pareti orizzontali
                    if ball_x - ball_size/2 <= field_left + margin or ball_x + ball_size/2 >= field_right - margin:
                        ball_dx = -ball_dx
                    # Paddle player
                    if (player_y <= ball_y - ball_size/2 <= player_y + paddle_h) and (player_x - paddle_w/2 <= ball_x <= player_x + paddle_w/2):
                        ball_dy = -ball_dy
                        ball_y = player_y + paddle_h + ball_size/2
                    # Paddle CPU
                    if (cpu_y - paddle_h <= ball_y + ball_size/2 <= cpu_y) and (cpu_x - paddle_w/2 <= ball_x <= cpu_x + paddle_w/2):
                        ball_dy = -ball_dy
                        ball_y = cpu_y - paddle_h - ball_size/2
                    # Bordo superiore
                    if ball_y + ball_size/2 >= field_top - margin:
                        ball_dy = -ball_dy
                    # Bordo inferiore
                    if ball_y - ball_size/2 <= field_bottom + margin:
                        ball_on_paddle = True
                        ball_dx = ball_dx_init
                        ball_dy = ball_dy_init

                # --- Genera path ---
                paths = []
                # paths.append(np.array([[0.0, 0.0]], dtype=np.float32))

                # Bordo campo
                fx = np.linspace(field_left, field_right, field_points)
                fy_top = np.full_like(fx, field_top)
                fy_bottom = np.full_like(fx, field_bottom)
                field_path = np.column_stack([np.concatenate([fx, fx[::-1]]),
                                              np.concatenate([fy_bottom, fy_top[::-1]])])
                paths.append(field_path)


                # --- NUOVI BORDI LATERALI (sinistra e destra) ---
                left_x = np.full(field_points, field_left)
                right_x = np.full(field_points, field_right)
                ly = np.linspace(field_bottom, field_top, field_points)

                left_wall = np.column_stack([left_x, ly])
                right_wall = np.column_stack([right_x, ly])

                paths.append(left_wall)
                paths.append(right_wall)

                # Paddle player
                px = np.linspace(player_x - paddle_w/2, player_x + paddle_w/2, paddle_points)
                py = np.full_like(px, player_y)
                paths.append(np.column_stack([px, py]))

                # Paddle CPU
                cx = np.linspace(cpu_x - paddle_w/2, cpu_x + paddle_w/2, paddle_points)
                cy = np.full_like(cx, cpu_y)
                paths.append(np.column_stack([cx, cy]))

                # Palla quadrato chiuso
                # Base inferiore
                bx = np.linspace(ball_x - ball_size/2, ball_x + ball_size/2, square_points_per_side)
                by = np.full_like(bx, ball_y - ball_size/2)
                # Lato destro
                bx = np.concatenate([bx, np.full(square_points_per_side, ball_x + ball_size/2)])
                by = np.concatenate([by, np.linspace(ball_y - ball_size/2, ball_y + ball_size/2, square_points_per_side)])
                # Base superiore
                bx = np.concatenate([bx, np.linspace(ball_x + ball_size/2, ball_x - ball_size/2, square_points_per_side)])
                by = np.concatenate([by, np.full(square_points_per_side, ball_y + ball_size/2)])
                # Lato sinistro
                bx = np.concatenate([bx, np.full(square_points_per_side, ball_x - ball_size/2)])
                by = np.concatenate([by, np.linspace(ball_y + ball_size/2, ball_y - ball_size/2, square_points_per_side)])
                paths.append(np.column_stack([bx, by]))
                # paths.append(np.array([[0.0, 0.0]], dtype=np.float32))

                # --- Combina path ---
                xy_points = make_xy_stream(paths, int(samplerate*frame_time))
                time.sleep(frame_time)

        except KeyboardInterrupt:
            pass

# --- Avvio ---
curses.wrapper(main)

