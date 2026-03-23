import { useRef, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import * as THREE from "three";

/* ─────────────────────────────────────────────────────────
   House3D — low-poly house built from Box + Cone primitives
───────────────────────────────────────────────────────── */
function House3D() {
  const group = useRef();

  useFrame((_, delta) => {
    if (group.current) {
      group.current.rotation.y += delta * 0.15;
    }
  });

  return (
    <Float speed={1.6} rotationIntensity={0.3} floatIntensity={0.8}>
      <group ref={group} scale={1.2}>
        {/* Base */}
        <mesh position={[0, -0.2, 0]}>
          <boxGeometry args={[1.8, 1.2, 1.4]} />
          <meshStandardMaterial
            color="#2a2f5b"
            transparent
            opacity={0.55}
            metalness={0.5}
            roughness={0.2}
          />
        </mesh>

        {/* Roof */}
        <mesh position={[0, 0.9, 0]} rotation={[0, Math.PI / 4, 0]}>
          <coneGeometry args={[1.5, 1, 4]} />
          <meshStandardMaterial
            color="#6366f1"
            transparent
            opacity={0.6}
            metalness={0.6}
            roughness={0.15}
          />
        </mesh>

        {/* Door */}
        <mesh position={[0, -0.45, 0.71]}>
          <boxGeometry args={[0.35, 0.55, 0.02]} />
          <meshStandardMaterial color="#818cf8" emissive="#818cf8" emissiveIntensity={0.5} />
        </mesh>

        {/* Window left */}
        <mesh position={[-0.5, 0.1, 0.71]}>
          <boxGeometry args={[0.3, 0.3, 0.02]} />
          <meshStandardMaterial color="#34d399" emissive="#34d399" emissiveIntensity={0.5} transparent opacity={0.7} />
        </mesh>

        {/* Window right */}
        <mesh position={[0.5, 0.1, 0.71]}>
          <boxGeometry args={[0.3, 0.3, 0.02]} />
          <meshStandardMaterial color="#34d399" emissive="#34d399" emissiveIntensity={0.5} transparent opacity={0.7} />
        </mesh>

        {/* Chimney */}
        <mesh position={[0.55, 1.1, -0.2]}>
          <boxGeometry args={[0.2, 0.5, 0.2]} />
          <meshStandardMaterial color="#4f46e5" transparent opacity={0.6} />
        </mesh>
      </group>
    </Float>
  );
}

/* ─────────────────────────────────────────────────────────
   OrbitParticles — glowing spheres on orbital paths
───────────────────────────────────────────────────────── */
function OrbitParticles({ count = 50 }) {
  const meshRef = useRef();

  const particles = useMemo(() => {
    const temp = [];
    for (let i = 0; i < count; i++) {
      const radius = 2.5 + Math.random() * 4;
      const speed = 0.1 + Math.random() * 0.4;
      const phase = Math.random() * Math.PI * 2;
      const tilt = (Math.random() - 0.5) * Math.PI * 0.6;
      const size = 0.02 + Math.random() * 0.06;
      const color = new THREE.Color().setHSL(
        0.6 + Math.random() * 0.2,   // blue-purple hue range
        0.7 + Math.random() * 0.3,
        0.5 + Math.random() * 0.3
      );
      temp.push({ radius, speed, phase, tilt, size, color });
    }
    return temp;
  }, [count]);

  const dummy = useMemo(() => new THREE.Object3D(), []);
  const colors = useMemo(() => {
    const arr = new Float32Array(count * 3);
    particles.forEach((p, i) => {
      arr[i * 3]     = p.color.r;
      arr[i * 3 + 1] = p.color.g;
      arr[i * 3 + 2] = p.color.b;
    });
    return arr;
  }, [particles, count]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    particles.forEach((p, i) => {
      const angle = t * p.speed + p.phase;
      dummy.position.set(
        Math.cos(angle) * p.radius,
        Math.sin(p.tilt) * Math.sin(angle) * p.radius * 0.5,
        Math.sin(angle) * p.radius
      );
      dummy.scale.setScalar(p.size * (1 + 0.3 * Math.sin(t * 2 + p.phase)));
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[null, null, count]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshStandardMaterial
        emissive="#6366f1"
        emissiveIntensity={2}
        toneMapped={false}
        transparent
        opacity={0.8}
      />
      <instancedBufferAttribute attach="instanceColor" args={[colors, 3]} />
    </instancedMesh>
  );
}

/* ─────────────────────────────────────────────────────────
   AccentRings — torus geometries rotating at different speeds
───────────────────────────────────────────────────────── */
function AccentRings() {
  const ring1 = useRef();
  const ring2 = useRef();
  const ring3 = useRef();

  useFrame((_, delta) => {
    if (ring1.current) ring1.current.rotation.x += delta * 0.2;
    if (ring1.current) ring1.current.rotation.z += delta * 0.05;
    if (ring2.current) ring2.current.rotation.y += delta * 0.15;
    if (ring2.current) ring2.current.rotation.x += delta * 0.08;
    if (ring3.current) ring3.current.rotation.z += delta * 0.12;
    if (ring3.current) ring3.current.rotation.y += delta * 0.1;
  });

  const ringMat = (color, emissive) => ({
    color,
    emissive,
    emissiveIntensity: 0.6,
    transparent: true,
    opacity: 0.2,
    metalness: 0.8,
    roughness: 0.1,
    side: THREE.DoubleSide,
  });

  return (
    <>
      <mesh ref={ring1} rotation={[0.5, 0, 0]}>
        <torusGeometry args={[3.2, 0.015, 16, 100]} />
        <meshStandardMaterial {...ringMat("#6366f1", "#6366f1")} />
      </mesh>
      <mesh ref={ring2} rotation={[1.2, 0.4, 0]}>
        <torusGeometry args={[4, 0.012, 16, 100]} />
        <meshStandardMaterial {...ringMat("#34d399", "#34d399")} />
      </mesh>
      <mesh ref={ring3} rotation={[0.3, 1, 0.5]}>
        <torusGeometry args={[3.6, 0.01, 16, 100]} />
        <meshStandardMaterial {...ringMat("#a78bfa", "#a78bfa")} />
      </mesh>
    </>
  );
}

/* ─────────────────────────────────────────────────────────
   MouseCamera — parallax camera rig following mouse
───────────────────────────────────────────────────────── */
function MouseCamera() {
  const { camera } = useThree();
  const mouse = useRef({ x: 0, y: 0 });
  const target = useRef({ x: 0, y: 0 });

  // Track mouse
  useMemo(() => {
    const handler = (e) => {
      mouse.current.x = (e.clientX / window.innerWidth - 0.5) * 2;
      mouse.current.y = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, []);

  useFrame(() => {
    // Smooth lerp toward mouse position
    target.current.x += (mouse.current.x * 1.2 - target.current.x) * 0.02;
    target.current.y += (-mouse.current.y * 0.8 - target.current.y) * 0.02;
    camera.position.x = target.current.x;
    camera.position.y = target.current.y + 0.5;
    camera.lookAt(0, 0, 0);
  });

  return null;
}

/* ─────────────────────────────────────────────────────────
   StarField — tiny background star points
───────────────────────────────────────────────────────── */
function StarField({ count = 200 }) {
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      arr[i * 3]     = (Math.random() - 0.5) * 25;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 25;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 25;
    }
    return arr;
  }, [count]);

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={count}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial color="#818cf8" size={0.03} sizeAttenuation transparent opacity={0.6} />
    </points>
  );
}

/* ─────────────────────────────────────────────────────────
   Main export — the full 3D canvas scene
───────────────────────────────────────────────────────── */
export default function HeroScene3D() {
  return (
    <div className="hero-3d-canvas">
      <Canvas
        camera={{ position: [0, 0.5, 6], fov: 50 }}
        dpr={[1, 1.5]}
        gl={{ alpha: true, antialias: true }}
        style={{ background: "transparent" }}
      >
        {/* Lighting */}
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={1} color="#6366f1" />
        <pointLight position={[-5, -3, 3]} intensity={0.6} color="#34d399" />
        <pointLight position={[0, 3, -5]} intensity={0.4} color="#a78bfa" />

        {/* Scene content */}
        <House3D />
        <OrbitParticles count={50} />
        <AccentRings />
        <StarField count={200} />
        <MouseCamera />
      </Canvas>
    </div>
  );
}
