import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';
import { MotionValue } from 'framer-motion';
import { MeshTransmissionMaterial, Sparkles } from '@react-three/drei';
import type { VoiceState } from './useVoiceSession';

// 3D Simplex Noise by Ian McEwan, Ashima Arts
const glslNoise = `
vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}
float snoise(vec3 v){ 
  const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
  const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i  = floor(v + dot(v, C.yyy) );
  vec3 x0 =   v - i + dot(i, C.xxx) ;
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min( g.xyz, l.zxy );
  vec3 i2 = max( g.xyz, l.zxy );
  vec3 x1 = x0 - i1 + 1.0 * C.xxx;
  vec3 x2 = x0 - i2 + 2.0 * C.xxx;
  vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
  i = mod(i, 289.0 ); 
  vec4 p = permute( permute( permute( 
             i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
           + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) 
           + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
  float n_ = 1.0/7.0; // N=7
  vec3  ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z *ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_ );
  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4( x.xy, y.xy );
  vec4 b1 = vec4( x.zw, y.zw );
  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
  vec3 p0 = vec3(a0.xy,h.x);
  vec3 p1 = vec3(a0.zw,h.y);
  vec3 p2 = vec3(a1.xy,h.z);
  vec3 p3 = vec3(a1.zw,h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
}
`;

const FluidEnergyMaterial = {
  uniforms: {
    uTime: { value: 0 },
    uAmplitude: { value: 0 },
    uColor: { value: new THREE.Color('#00ffff') },
    uStateSpeed: { value: 1.0 }
  },
  vertexShader: `
    ${glslNoise}
    uniform float uTime;
    uniform float uAmplitude;
    uniform float uStateSpeed;
    varying vec2 vUv;
    varying float vNoise;
    
    void main() {
      vUv = uv;
      // Irregular paths via noise
      vec3 noisePos = position * 2.0 + uTime * 0.3 * uStateSpeed;
      vNoise = snoise(noisePos);
      
      // displace vertices
      float displacement = vNoise * (0.15 + uAmplitude * 0.4);
      vec3 newPos = position + normal * displacement;
      
      gl_Position = projectionMatrix * modelViewMatrix * vec4(newPos, 1.0);
    }
  `,
  fragmentShader: `
    uniform vec3 uColor;
    uniform float uAmplitude;
    varying vec2 vUv;
    varying float vNoise;
    
    void main() {
      // Create glowing bands using sine of noise
      float band = sin(vNoise * 30.0);
      float alpha = smoothstep(0.9, 1.0, band);
      
      // Boost core lines
      vec3 glowColor = uColor * (1.5 + uAmplitude * 2.0);
      
      gl_FragColor = vec4(glowColor, alpha * 0.9);
    }
  `
};

const colorStops = [
  new THREE.Color('#00ffff'), // Electric Blue
  new THREE.Color('#8a2be2'), // Violet
  new THREE.Color('#ff00ff'), // Magenta
  new THREE.Color('#ff8c00'), // Warm Orange
  new THREE.Color('#dc143c'), // Crimson
];

const getCurrentColor = (time: number) => {
  const speed = 0.4;
  const t = time * speed;
  const index = Math.floor(t) % colorStops.length;
  const nextIndex = (index + 1) % colorStops.length;
  const mixFactor = t - Math.floor(t);
  const smoothMix = mixFactor * mixFactor * (3.0 - 2.0 * mixFactor);
  const c = new THREE.Color();
  c.lerpColors(colorStops[index], colorStops[nextIndex], smoothMix);
  return c;
};

interface OrbProps {
  state: VoiceState;
  amplitude: MotionValue<number>;
  size?: number;
}

const AI_Core = ({ state, amplitude }: { state: VoiceState, amplitude: MotionValue<number> }) => {
  const glassRef = useRef<THREE.Mesh>(null);
  const energyRef = useRef<THREE.ShaderMaterial>(null);
  const coreRef = useRef<THREE.MeshStandardMaterial>(null);
  const particlesRef = useRef<THREE.Group>(null);
  
  const glassMatRef = useRef<any>(null); // To store MeshTransmissionMaterial ref if needed

  useFrame((stateObj, delta) => {
    const time = stateObj.clock.elapsedTime;
    const targetAmp = amplitude.get();
    
    // Smooth amplitude
    const currentAmp = energyRef.current?.uniforms.uAmplitude.value || 0;
    const smoothedAmp = THREE.MathUtils.lerp(currentAmp, targetAmp, 0.15);
    
    // Speed based on state
    let targetSpeed = 1.0;
    if (state === 'listening' || state === 'speaking') targetSpeed = 1.5;
    if (state === 'thinking') targetSpeed = 2.5;
    const currentSpeed = energyRef.current?.uniforms.uStateSpeed.value || 1.0;
    const smoothedSpeed = THREE.MathUtils.lerp(currentSpeed, targetSpeed, 0.05);

    // Get current procedural color
    const currentColor = getCurrentColor(time);

    // Update Energy Layer (Spirograph)
    if (energyRef.current) {
      energyRef.current.uniforms.uTime.value = time;
      energyRef.current.uniforms.uAmplitude.value = smoothedAmp;
      energyRef.current.uniforms.uStateSpeed.value = smoothedSpeed;
      energyRef.current.uniforms.uColor.value.copy(currentColor);
    }
    
    // Update Core Layer
    if (coreRef.current) {
      coreRef.current.emissive.copy(currentColor);
      coreRef.current.emissiveIntensity = 0.5 + smoothedAmp * 1.5;
    }

    // Update Outer Glass Shell (Deformation 1-4% via scale + color tint)
    if (glassRef.current) {
      // Slow rotation
      glassRef.current.rotation.y += delta * 0.1 * smoothedSpeed;
      glassRef.current.rotation.x += delta * 0.05 * smoothedSpeed;
      
      // Deformation via scale (1-4%)
      const breathe = Math.sin(time * 2.0) * 0.01;
      const ampDeform = smoothedAmp * 0.04; 
      const scale = 1.0 + breathe + ampDeform;
      glassRef.current.scale.setScalar(scale);
    }
    
    if (glassMatRef.current) {
      // Subtle color tint for glass
      glassMatRef.current.color.copy(currentColor).lerp(new THREE.Color('#ffffff'), 0.8);
    }

    // Update Particles
    if (particlesRef.current) {
      particlesRef.current.rotation.y -= delta * 0.05 * smoothedSpeed;
    }
  });

  return (
    <group>
      {/* Layer D: Outer Glass Shell */}
      <mesh ref={glassRef}>
        <sphereGeometry args={[1.2, 64, 64]} />
        <MeshTransmissionMaterial
          ref={glassMatRef}
          backside
          backsideThickness={0.5}
          thickness={0.5}
          chromaticAberration={0.05}
          anisotropicBlur={0.1}
          clearcoat={1}
          clearcoatRoughness={0.1}
          roughness={0.1}
          transmission={1.0}
          ior={1.5}
          resolution={256}
        />
        
        {/* Layer B: Fluid Energy (Spirograph) */}
        <mesh>
          <sphereGeometry args={[0.9, 128, 64]} />
          <shaderMaterial
            ref={energyRef}
            args={[FluidEnergyMaterial]}
            wireframe={true}
            transparent={true}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            side={THREE.DoubleSide}
          />
        </mesh>
        
        {/* Layer A: Glowing Core */}
        <mesh scale={0.4}>
          <sphereGeometry args={[1, 32, 32]} />
          <meshStandardMaterial
            ref={coreRef}
            color="#ffffff"
            emissive="#00ffff"
            emissiveIntensity={1}
            transparent={true}
            opacity={0.8}
          />
        </mesh>

        {/* Layer C: Fine Particles */}
        <group ref={particlesRef}>
          <Sparkles 
            count={200} 
            scale={1.5} 
            size={2} 
            speed={0.4} 
            opacity={0.6}
            noise={0.5} 
            color="#ffffff" 
          />
        </group>
      </mesh>
    </group>
  );
};

export const Orb = ({ state, amplitude, size = 300 }: OrbProps) => {
  // Determine scale based on state using pure CSS transform for smooth entry
  let scale = 1.0;
  if (state === 'entering') scale = 0.01;
  else if (state === 'thinking' || state === 'speaking') scale = 1.05;

  return (
    <div className="relative flex items-center justify-center transition-transform duration-700 ease-out z-10" 
         style={{ width: size, height: size, transform: `scale(${scale})` }}>
      <Canvas 
        camera={{ position: [0, 0, 3.5], fov: 45 }}
        dpr={[1, 2]}
        gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }}
      >
        <color attach="background" args={['#020205']} />
        
        {/* Lighting */}
        <ambientLight intensity={0.2} />
        <directionalLight position={[5, 5, 5]} intensity={1} color="#ffffff" />
        <directionalLight position={[-5, -5, -5]} intensity={0.5} color="#8a2be2" />
        
        <AI_Core state={state} amplitude={amplitude} />
        
        <EffectComposer>
          <Bloom 
            luminanceThreshold={0.2} 
            luminanceSmoothing={0.9} 
            intensity={1.2} 
            mipmapBlur 
          />
        </EffectComposer>
      </Canvas>
    </div>
  );
};
