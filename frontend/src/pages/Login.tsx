import { FormEvent, useEffect, useRef, useState } from "react";
import { Hexagon, Lock, User } from "lucide-react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { layoutWithLines, prepareWithSegments, type PreparedTextWithSegments } from "@chenglou/pretext";

import { isAuthenticated, login, saveAuth } from "../lib/auth";

const dreamPoem =
  "海客谈瀛洲，烟涛微茫信难求。越人语天姥，云霞明灭或可睹。天姥连天向天横，势拔五岳掩赤城。天台四万八千丈，对此欲倒东南倾。我欲因之梦吴越，一夜飞度镜湖月。湖月照我影，送我至剡溪。谢公宿处今尚在，渌水荡漾清猿啼。脚著谢公屐，身登青云梯。半壁见海日，空中闻天鸡。千岩万转路不定，迷花倚石忽已暝。熊咆龙吟殷岩泉，栗深林兮惊层巅。云青青兮欲雨，水澹澹兮生烟。列缺霹雳，丘峦崩摧。洞天石扉，訇然中开。青冥浩荡不见底，日月照耀金银台。霓为衣兮风为马，云之君兮纷纷而来下。虎鼓瑟兮鸾回车，仙之人兮列如麻。忽魂悸以魄动，恍惊起而长嗟。惟觉时之枕席，失向来之烟霞。";

interface PoemLayer {
  font: string;
  lineHeight: number;
  anchorX: number;
  anchorY: number;
  colorRgb: string;
  baseAlpha: number;
  glyphs: Glyph[];
}

interface Glyph {
  char: string;
  x: number;
  y: number;
}

type PoemLayout = PoemLayer[];

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export default function LoginPage() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const poemLayoutRef = useRef<PoemLayout | null>(null);
  const pointerRef = useRef({ x: -9999, y: -9999 });
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    let rafId = 0;

    const buildLayerGlyphs = (
      prepared: PreparedTextWithSegments,
      font: string,
      lineHeight: number,
      maxWidth: number,
    ): Glyph[] => {
      context.font = font;
      const layout = layoutWithLines(prepared, maxWidth, lineHeight);
      const glyphs: Glyph[] = [];

      layout.lines.forEach((line, lineIndex) => {
        let x = 0;
        const chars = Array.from(line.text);
        chars.forEach((char) => {
          const width = context.measureText(char).width;
          glyphs.push({
            char,
            x,
            y: lineIndex * lineHeight,
          });
          x += width;
        });
      });

      return glyphs;
    };

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;

      const fontSize = Math.max(26, Math.min(19, window.innerWidth / 92));
      const lineHeight = Math.round(fontSize * 1.92);
      const font = `${fontSize}px "Noto Serif SC", "Songti SC", serif`;
      const maxWidth = window.innerWidth;

      const charsPerLine = Math.max(28, Math.floor(maxWidth / Math.max(fontSize * 0.96, 1)));
      const lineCount = Math.ceil(window.innerHeight / Math.max(lineHeight, 1)) + 8;
      const repeatsNeeded = Math.ceil((charsPerLine * lineCount) / dreamPoem.length) + 8;
      const repeatedDreamPoem = Array.from({ length: repeatsNeeded }, () => dreamPoem).join("\t\t\t");
      const prepared = prepareWithSegments(repeatedDreamPoem, font, { whiteSpace: "pre-wrap" });

      poemLayoutRef.current = [
        {
          font,
          lineHeight,
          anchorX: 0,
          anchorY: fontSize,
          colorRgb: "108, 132, 185",
          baseAlpha: 0.19,
          glyphs: buildLayerGlyphs(prepared, font, lineHeight, maxWidth),
        },
      ];
    };

    const handleMove = (event: MouseEvent) => {
      pointerRef.current = { x: event.clientX, y: event.clientY };
    };

    const handleTouch = (event: TouchEvent) => {
      const touch = event.touches[0];
      if (!touch) {
        return;
      }
      pointerRef.current = { x: touch.clientX, y: touch.clientY };
    };

    const resetPointer = () => {
      pointerRef.current = { x: -9999, y: -9999 };
    };

    const drawLayer = (layer: PoemLayer) => {
      context.save();
      context.translate(layer.anchorX, layer.anchorY);
      context.font = layer.font;
      layer.glyphs.forEach((glyph) => {
        const baseX = layer.anchorX + glyph.x;
        const baseY = layer.anchorY + glyph.y;
        const deltaX = baseX - pointerRef.current.x;
        const deltaY = baseY - pointerRef.current.y;
        const distance = Math.hypot(deltaX, deltaY);

        const repelRadius = 118;
        const normalized = clamp(1 - distance / repelRadius, 0, 1);
        const repelForce = normalized * normalized;
        const maxPush = 34;

        const unitX = distance === 0 ? 0 : deltaX / distance;
        const unitY = distance === 0 ? 0 : deltaY / distance;
        const offsetX = unitX * maxPush * repelForce;
        const offsetY = unitY * maxPush * 0.62 * repelForce;

        const fade = 1 - repelForce * 0.9;
        const finalAlpha = clamp(layer.baseAlpha * fade, 0.03, layer.baseAlpha);
        context.fillStyle = `rgba(${layer.colorRgb}, ${finalAlpha})`;

        context.fillText(glyph.char, glyph.x + offsetX, glyph.y + offsetY);
      });
      context.restore();
    };

    const draw = () => {
      context.clearRect(0, 0, canvas.width, canvas.height);

      const poemLayout = poemLayoutRef.current;
      if (poemLayout) {
        poemLayout.forEach((layer) => drawLayer(layer));
      }

      rafId = window.requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseleave", resetPointer);
    window.addEventListener("touchmove", handleTouch, { passive: true });
    window.addEventListener("touchend", resetPointer, { passive: true });
    draw();

    return () => {
      window.cancelAnimationFrame(rafId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseleave", resetPointer);
      window.removeEventListener("touchmove", handleTouch);
      window.removeEventListener("touchend", resetPointer);
    };
  }, []);

  const fromPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/create";

  if (isAuthenticated()) {
    return <Navigate to={fromPath} replace />;
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await login({ username, password, rememberMe });
      saveAuth(result.accessToken, result.expiresIn, rememberMe);
      navigate(fromPath, { replace: true });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "登录失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-stage">
      <canvas ref={canvasRef} className="ink-canvas" aria-hidden="true" />
      <div className="poetry-noise" aria-hidden="true" />

      <main className="login-shell">
        <div className="login-brand">
          <span className="brand-icon">
            <Hexagon className="h-6 w-6" />
          </span>
          <h1>ReWritter</h1>
          <p>多智能体文本分析学习平台</p>
        </div>

        <form className="login-card" onSubmit={onSubmit}>
          <label className="login-field">
            <span>* 用户名</span>
            <div className="input-wrap">
              <User className="h-4 w-4" />
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="请输入用户名"
                autoComplete="username"
                required
              />
            </div>
          </label>

          <label className="login-field">
            <span>* 密码</span>
            <div className="input-wrap">
              <Lock className="h-4 w-4" />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="请输入密码"
                autoComplete="current-password"
                required
              />
            </div>
          </label>

          <label className="remember-row">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(event) => setRememberMe(event.target.checked)}
            />
            记住我
          </label>

          {error && <p className="login-error">{error}</p>}

          <button type="submit" disabled={loading} className="login-submit">
            {loading ? "登录中..." : "登录"}
          </button>

          <p className="login-tip">默认账号：admin / admin123</p>
        </form>

        <footer className="login-footer">
          <p>© 2026 ReWritter. All rights reserved.</p>
          <p>本系统仅用于学习研究；请勿用于任何违法用途。</p>
        </footer>
      </main>
    </div>
  );
}
