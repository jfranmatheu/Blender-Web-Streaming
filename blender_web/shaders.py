import bpy
import gpu


if not bpy.app.background:
    IMAGE_SHADER = gpu.types.GPUShader(
"""
uniform mat4 ModelViewProjectionMatrix;
in vec2 texco;
in vec2 pos;
out vec2 texco_interp;
void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0, 1.0);
    texco_interp = texco;
}
""",
"""
vec4 toLinear(vec4 sRGB)
{
    bvec3 cutoff = lessThan(sRGB.rgb, vec3(0.04045));
    vec3 higher = pow((sRGB.rgb + vec3(0.055))/vec3(1.055), vec3(2.4));
    vec3 lower = sRGB.rgb/vec3(12.92);

    return vec4(mix(higher, lower, cutoff), sRGB.a);
}

in vec2 texco_interp;
out vec4 fragColor;
uniform sampler2D image;
void main()
{
    fragColor = texture(image, texco_interp);
    fragColor.rgb = toLinear(fragColor); // fast method: pow(fragColor.rgb, vec3(2.2));
}
"""
    )