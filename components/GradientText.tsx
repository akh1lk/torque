import React, { ReactNode } from 'react';

interface GradientTextProps {
    children: ReactNode;
    className?: string;
    colors?: string[];
    animationSpeed?: number;
    showBorder?: boolean;
}

export default function GradientText({
    children,
    className = "",
    colors = ["#ffaa40", "#9c40ff", "#ffaa40"],
    animationSpeed = 8,
    showBorder = false,
}: GradientTextProps) {
    // Ensure seamless looping by adding the first color at the end if it's not already there
    const loopingColors = colors[colors.length - 1] === colors[0] ? colors : [...colors, colors[0]];
    
    // Create a unique animation name to avoid conflicts
    const animationName = `gradientLoop${Math.random().toString(36).substr(2, 9)}`;
    
    const gradientStyle = {
        backgroundImage: `linear-gradient(90deg, ${loopingColors.join(", ")})`,
        backgroundSize: "200% 100%",
        animation: `${animationName} ${animationSpeed}s linear infinite`,
    };

    return (
        <>
            <style dangerouslySetInnerHTML={{
                __html: `
                    @keyframes ${animationName} {
                        0% { background-position: 0% 0%; }
                        100% { background-position: 200% 0%; }
                    }
                `
            }} />
            <div
                className={`relative flex max-w-fit flex-row items-center justify-start overflow-hidden ${className}`}
            >
            {showBorder && (
                <div
                    className="absolute inset-0 bg-cover z-0 pointer-events-none"
                    style={{
                        ...gradientStyle,
                    }}
                >
                    <div
                        className="absolute inset-0 bg-black rounded-[1.25rem] z-[-1]"
                        style={{
                            width: "calc(100% - 2px)",
                            height: "calc(100% - 2px)",
                            left: "50%",
                            top: "50%",
                            transform: "translate(-50%, -50%)",
                        }}
                    ></div>
                </div>
            )}
            <div
                className="inline-block relative z-2 text-transparent bg-cover font-bold"
                style={{
                    ...gradientStyle,
                    backgroundClip: "text",
                    WebkitBackgroundClip: "text",
                }}
            >
                {children}
            </div>
        </div>
        </>
    );
}
